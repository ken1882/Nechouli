from module.webui.utils import (
    get_localstorage,
    set_localstorage,
)
from pywebio.output import (
    Output,
    clear,
    close_popup,
    popup,
    put_button,
    put_buttons,
    put_collapse,
    put_column,
    put_error,
    put_html,
    put_link,
    put_loading,
    put_markdown,
    put_row,
    put_scope,
    put_table,
    put_text,
    put_warning,
    put_image,
    toast,
    use_scope,
)
from pywebio.input import textarea
from module.webui.process_manager import ProcessManager
from module.webui.updater import updater
from module.base.utils import (
    str2int,
    kill_remote_browser,
    check_connection,
    get_all_instance_addresses
)

import time
import random
import hashlib
import threading

def _deterministic_jitter(name: str, window: float, epoch_bucket: int = 30) -> float:
    """
    Deterministic per-(name, time-bucket) jitter in [0, window].
    Using a stable seed means multiple processes pick the *same* offset,
    keeping starts uniformly spread instead of bunching by chance.
    """
    bucket = int(time.time() // epoch_bucket)
    seed = f"{name}:{bucket}".encode()
    h = hashlib.blake2b(seed, digest_size=8).digest()
    rnd = random.Random(h)         # independent RNG with deterministic seed
    return rnd.uniform(0.0, max(0.0, window))

def run_all_instances(
        spread_base: float = 0.75,
        spread_cap: float = 20.0,
        epoch_bucket: int = 30
    ):
    """
    Fire-and-forget: start any not-alive instances in a background thread,
    jittered to avoid a thundering herd. Returns immediately.

    spread_base  : seconds per instance to size the start window.
    spread_cap   : max window size in seconds.
    epoch_bucket : jitter seed changes every N seconds (keeps spread stable briefly).
    """
    help = '# List of profile names not to start, separated by line',
    buts = textarea(
        'Exception List',
        code = {
            'mode': "markdown",
            'theme': 'darcula',
        },
        value=get_localstorage('start_buts', help)
    )
    set_localstorage('start_buts', buts)
    buts = [l.strip() for l in str(buts).split('\n')]
    buts = [l for l in buts if not l.startswith('#')]
    popup('Please wait')

    ins = get_all_instance_addresses()
    to_start = [
        (name, addr) for name, addr in ins.items()
        if not ProcessManager.get_manager(name).alive and name not in buts
    ]

    if not to_start:
        popup('Started', 'All instances already running')
        return None

    # Precompute schedule in main thread (still non-blocking)
    n = len(to_start)
    window = min(spread_cap, max(spread_base, spread_base * n))
    schedule = []
    for name, addr in to_start:
        offset = _deterministic_jitter(name, window, epoch_bucket)
        schedule.append((offset, name, addr))
    schedule.sort(key=lambda x: x[0])  # earliest first

    def _worker():
        t0 = time.monotonic()
        for offset, name, addr in schedule:
            # Sleep only inside the worker thread
            delta = offset - (time.monotonic() - t0)
            if delta > 0:
                time.sleep(delta)

            # Re-check liveness just before starting
            alas = ProcessManager.get_manager(name)
            if alas.alive:
                continue

            try:
                alas.start(None, updater.event)
            except Exception as e:
                print("Failed to start %s (%s): %s", name, addr, e)

    th = threading.Thread(target=_worker, name="InstanceStarter", daemon=True)
    th.start()
    popup('Statred', '\n'.join([f'{n} {a}' for n,a in to_start]))
    return th


def stop_all_instances():
    help = '# List of profile names not to stop, separated by line'
    buts = textarea(
        'Exception List',
        code = {
            'mode': "markdown",
            'theme': 'darcula',
        },
        value=get_localstorage('stop_buts', help),
    )
    set_localstorage('stop_buts', buts)
    buts = [l.strip() for l in str(buts).split('\n')]
    buts = [l for l in buts if not l.startswith('#')]
    popup('Please wait')
    ins = get_all_instance_addresses()
    msg = ''
    for name, addr in ins.items():
        if name in buts:
            continue
        alas = ProcessManager.get_manager(name)
        if not alas.alive:
            continue
        alas.stop()
        msg += f'{name} {addr}\n'
    popup('Stopped', msg)

def show_instances_status():
    popup('Please wait')
    ins = get_all_instance_addresses()
    msg = ''
    for name, addr in ins.items():
        alas = ProcessManager.get_manager(name)
        msg += f'{name} {addr} {"Running" if alas.alive else "Stopped"} {"O" if check_connection(addr, timeout=0.1) else "X"}\n'
    popup('Status', msg)
