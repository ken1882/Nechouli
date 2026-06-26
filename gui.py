import threading
from multiprocessing import Event, Process

from module.base.utils import kill_process_tree
from module.logger import logger
from module.webui.setting import State


def func(ev, stop_ev=None):
    import argparse
    import asyncio
    import signal
    import sys

    import uvicorn

    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    State.restart_event = ev

    parser = argparse.ArgumentParser(description="Alas web service")
    parser.add_argument(
        "--host",
        type=str,
        help="Host to listen. Default to WebuiHost in deploy setting",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Port to listen. Default to WebuiPort in deploy setting",
    )
    parser.add_argument(
        "-k", "--key", type=str, help="Password of alas. No password by default"
    )
    parser.add_argument(
        "--cdn",
        action="store_true",
        help="Use jsdelivr cdn for pywebio static files (css, js). Self host cdn by default.",
    )
    parser.add_argument(
        "--electron", action="store_true", help="Runs by electron client."
    )
    parser.add_argument(
        "--run",
        nargs="+",
        type=str,
        help="Run alas by config names on startup",
    )
    args, _ = parser.parse_known_args()

    host = args.host or State.deploy_config.WebuiHost or "0.0.0.0"
    port = args.port or int(State.deploy_config.WebuiPort) or 22367
    State.electron = args.electron

    logger.hr("Launcher config")
    logger.attr("Host", host)
    logger.attr("Port", port)
    logger.attr("Electron", args.electron)
    logger.attr("Reload", ev is not None)

    if State.electron:
        # https://github.com/LmeSzinc/AzurLaneAutoScript/issues/2051
        logger.info("Electron detected, remove log output to stdout")
        from module.logger.logger import console_hdlr
        logger.removeHandler(console_hdlr)

    config = uvicorn.Config("module.webui.app:app", host=host, port=port, factory=True)
    server = uvicorn.Server(config)

    def request_exit(*_):
        logger.info("Shutdown signal received, stopping web service")
        server.should_exit = True
        if stop_ev is not None:
            stop_ev.set()

    signal.signal(signal.SIGINT, request_exit)
    signal.signal(signal.SIGTERM, request_exit)

    if stop_ev is not None:
        def wait_for_stop():
            stop_ev.wait()
            server.should_exit = True

        threading.Thread(target=wait_for_stop, daemon=True).start()

    try:
        server.run()
    finally:
        try:
            from module.webui.app import clearup
            clearup()
        except Exception as e:
            logger.exception(e)


def stop_process(process, stop_event=None):
    if process is None:
        return
    if stop_event is not None:
        stop_event.set()
    try:
        if process.is_alive():
            process.join(timeout=10)
    except KeyboardInterrupt:
        logger.info("Second keyboard interrupt received, force killing web service")
    finally:
        if process.is_alive():
            kill_process_tree(process.pid, grace=1)
            process.kill()
        try:
            process.join(timeout=1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt during forced shutdown, exiting")


if __name__ == "__main__":
    if State.deploy_config.EnableReload:
        should_exit = False
        while not should_exit:
            event = Event()
            stop_event = Event()
            process = Process(target=func, args=(event, stop_event))
            process.start()
            try:
                while not should_exit:
                    try:
                        b = event.wait(1)
                    except KeyboardInterrupt:
                        logger.info("Keyboard interrupt received, stopping web service")
                        should_exit = True
                        break
                    if b:
                        stop_event.set()
                        break
                    elif process.is_alive():
                        continue
                    else:
                        should_exit = True
            finally:
                stop_process(process, stop_event)
    else:
        try:
            func(None)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping web service")
