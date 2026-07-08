import argparse
import os
import queue
import threading
from multiprocessing import Process
from typing import Dict, List, Union

import inflection
from filelock import FileLock, Timeout
from rich.console import Console, ConsoleRenderable

from module.config.utils import filepath_config
from module.logger.logger import WEB_LOG_WRAP_WIDTH
from module.logger import logger, set_file_logger, set_func_logger
from module.webui.fake import get_config_mod, mod_instance
from module.webui.setting import State
from module.webui.submodule.utils import get_available_func
from module.base.utils import kill_process_tree, kill_remote_browser

class ProcessManager:
    _processes: Dict[str, "ProcessManager"] = {}

    def __init__(self, config_name: str = "alas") -> None:
        self.config_name = config_name
        self._renderable_queue: queue.Queue[ConsoleRenderable] = State.manager.Queue()
        self.renderables: List[ConsoleRenderable] = []
        self.renderable_line_counts: List[int] = []
        self.renderables_version = 0
        self.renderables_max_length = 100
        self.renderables_reduce_length = 100
        self._process: Process = None
        self.thd_log_queue_handler: threading.Thread = None
        logger.info(f"ProcessManager created: {config_name}")

    def start(self, func, ev: threading.Event = None) -> None:
        if not self.alive:
            if func is None:
                func = get_config_mod(self.config_name)
            self._process = Process(
                target=ProcessManager.run_process,
                args=(
                    self.config_name,
                    func,
                    self._renderable_queue,
                    ev,
                ),
            )
            self._process.start()
            self.start_log_queue_handler()

    def start_log_queue_handler(self):
        if (
            self.thd_log_queue_handler is not None
            and self.thd_log_queue_handler.is_alive()
        ):
            return
        self.thd_log_queue_handler = threading.Thread(
            target=self._thread_log_queue_handler,
            daemon=True,
        )
        self.thd_log_queue_handler.start()

    def stop(self) -> None:
        lock = FileLock(f"{filepath_config(self.config_name)}.lock")
        try:
            lock.acquire(timeout=2)
        except Timeout:
            logger.warning(f"Timeout waiting for process lock: {self.config_name}")
        try:
            if self.alive:
                kill_process_tree(self._process.pid, grace=5)
                self._append_renderable(
                    f"[{self.config_name}] exited. Reason: Manual stop\n"
                )
        finally:
            if lock.is_locked:
                lock.release()
        if self.thd_log_queue_handler is not None:
            self.thd_log_queue_handler.join(timeout=1)
            if self.thd_log_queue_handler.is_alive():
                logger.warning(
                    "Log queue handler thread does not stop within 1 seconds"
                )
        logger.info(f"[{self.config_name}] exited")

    def _thread_log_queue_handler(self) -> None:
        while self.alive:
            try:
                log = self._renderable_queue.get(timeout=1)
            except queue.Empty:
                continue
            self._append_renderable(log)
        logger.info("End of log queue handler loop")

    def _append_renderable(self, renderable: ConsoleRenderable) -> None:
        renderable, line_count = self._limit_renderable_lines(renderable)
        self.renderables.append(renderable)
        self.renderable_line_counts.append(line_count)
        self._trim_renderables()

    def _limit_renderable_lines(self, renderable: ConsoleRenderable) -> tuple[ConsoleRenderable, int]:
        if isinstance(renderable, str):
            return self._limit_string_lines(renderable)

        lines = self._renderable_to_lines(renderable)
        if len(lines) <= self.renderables_max_length:
            return renderable, max(1, len(lines))

        lines = lines[-self.renderables_max_length:]
        self.renderables_version += 1
        return "\n".join(lines) + "\n", self.renderables_max_length

    def _limit_string_lines(self, text: str) -> tuple[str, int]:
        chunks = []
        truncated = False

        for line in reversed(text.splitlines() or [""]):
            line_chunks = [
                line[max(0, end - WEB_LOG_WRAP_WIDTH):end]
                for end in range(len(line), 0, -WEB_LOG_WRAP_WIDTH)
            ] or [""]
            for chunk in line_chunks:
                chunks.append(chunk)
                if len(chunks) >= self.renderables_max_length:
                    truncated = True
                    break
            if truncated:
                break

        chunks.reverse()
        line_count = max(1, len(chunks))
        wrapped = "\n".join(chunks) + "\n"
        if truncated or wrapped != text:
            self.renderables_version += 1
            return wrapped, line_count
        return text, line_count

    @staticmethod
    def _renderable_to_lines(renderable: ConsoleRenderable) -> List[str]:
        console = Console(no_color=True, force_terminal=False, width=80)
        with console.capture() as capture:
            console.print(renderable)
        return capture.get().splitlines()

    def _trim_renderables(self) -> None:
        total_lines = sum(self.renderable_line_counts)
        while total_lines > self.renderables_max_length and len(self.renderables) > 1:
            total_lines -= self.renderable_line_counts.pop(0)
            self.renderables.pop(0)
            self.renderables_version += 1

    @property
    def alive(self) -> bool:
        if self._process is not None:
            return self._process.is_alive()
        else:
            return False

    @property
    def state(self) -> int:
        if self.alive:
            return 1
        elif len(self.renderables) == 0:
            return 2
        else:
            console = Console(no_color=True)
            with console.capture() as capture:
                console.print(self.renderables[-1])
            s = capture.get().strip()
            if s.endswith("Reason: Manual stop"):
                return 2
            elif s.endswith("Reason: Finish"):
                return 2
            elif s.endswith("Reason: Update"):
                return 4
            else:
                return 3

    @classmethod
    def get_manager(cls, config_name: str) -> "ProcessManager":
        """
        Create a new alas if not exists.
        """
        if config_name not in cls._processes:
            cls._processes[config_name] = ProcessManager(config_name)
        return cls._processes[config_name]

    @staticmethod
    def run_process(
        config_name, func: str, q: queue.Queue, e: threading.Event = None
    ) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--electron", action="store_true", help="Runs by electron client."
        )
        args, _ = parser.parse_known_args()
        State.electron = args.electron

        # Setup logger
        set_file_logger(name=config_name)
        if State.electron:
            # https://github.com/LmeSzinc/AzurLaneAutoScript/issues/2051
            logger.info("Electron detected, remove log output to stdout")
            from module.logger.logger import console_hdlr
            logger.removeHandler(console_hdlr)
        set_func_logger(func=q.put)

        from module.config.config import AzurLaneConfig

        AzurLaneConfig.stop_event = e
        try:
            # Run alas
            if func == "alas":
                from module.alas import AzurLaneAutoScript
                from nch import Nechouli

                if e is not None:
                    AzurLaneAutoScript.stop_event = e
                Nechouli(config_name=config_name).loop()
            elif func in get_available_func():
                from nch import Nechouli

                Nechouli(config_name=config_name).run(inflection.underscore(func))
            else:
                logger.critical(f"No function matched: {func}")
            logger.info(f"[{config_name}] exited. Reason: Finish\n")
        except Exception as e:
            logger.exception(e)
        kill_remote_browser(config_name)

    @classmethod
    def running_instances(cls) -> List["ProcessManager"]:
        l = []
        for process in cls._processes.values():
            if process.alive:
                l.append(process)
        return l

    @staticmethod
    def restart_processes(
        instances: List[Union["ProcessManager", str]] = None, ev: threading.Event = None
    ):
        """
        After update and reload, or failed to perform an update,
        restart all alas that running before update
        """
        logger.hr("Restart alas")

        # Load MOD_CONFIG_DICT
        mod_instance()

        if instances is None:
            instances = []

        _instances = set()

        for instance in instances:
            if isinstance(instance, str):
                _instances.add(ProcessManager.get_manager(instance))
            elif isinstance(instance, ProcessManager):
                _instances.add(instance)

        try:
            with open("./config/reloadalas", mode="r") as f:
                for line in f.readlines():
                    line = line.strip()
                    _instances.add(ProcessManager.get_manager(line))
        except FileNotFoundError:
            pass

        for process in _instances:
            logger.info(f"Starting [{process.config_name}]")
            process.start(func=get_config_mod(process.config_name), ev=ev)

        try:
            os.remove("./config/reloadalas")
        except:
            pass
        logger.info("Start alas complete")
