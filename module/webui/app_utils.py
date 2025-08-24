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
import json
import hashlib
import threading
from datetime import datetime, timedelta
from module.config.utils import nearest_future

ScheduledStart = {}

def _get_next_run(config_name: str) -> tuple[str, datetime]:
    try:
        with open(f'config/{config_name}.json', 'r', encoding='utf-8') as f:
            conf = json.load(f)
            enabled_tasks = {}
            for task in conf.keys():
                if "Scheduler" not in conf[task]:
                    continue
                sched = conf[task]["Scheduler"]
                if not sched["Enable"]:
                    continue
                enabled_tasks[task] = datetime.strptime(sched["NextRun"], '%Y-%m-%d %H:%M:%S')
        ret_time = nearest_future(enabled_tasks.values())
        ret_task = next((k for k,v in enabled_tasks.items() if v==ret_time), None)
        return ret_task, ret_time
    except Exception:
        return None, None

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

    next_task_table = {}
    for name, _ in to_start:
        task, ttime = _get_next_run(name)
        if task and ttime:
            next_task_table[name] = (task, ttime)

    def _worker():
        global ScheduledStart
        nonlocal next_task_table
        t0 = time.monotonic()
        start_order = []
        for offset, name, addr in schedule:
            if name in ScheduledStart and datetime.now() < ScheduledStart[name]:
                continue
            base = 0
            # sleep until next scheduled task
            if name in next_task_table:
                task, ttime = next_task_table[name]
                if ttime > datetime.now():
                    base = (ttime - datetime.now()).total_seconds()
            else: # skip if no enabled task
                continue

            # Sleep only inside the worker thread
            delta = offset - (time.monotonic() - t0)
            st = max(0, base+delta)
            print(f"Delay start of {name} for {st:.2f} seconds (task: {task})")
            ScheduledStart[name] = datetime.now() + timedelta(seconds=int(st+0.5))
            start_order.append([name, addr, st])

        start_order.sort(key=lambda x: x[2])
        total = 0
        for i,dat in enumerate(start_order):
            v = dat[2]
            start_order[i][2] = v - total
            total = v

        for name, addr, delay in start_order:
            if delay > 0:
                print(f"Waiting {delay:.2f} seconds before starting {name} ({addr})")
                time.sleep(delay)

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
    msg = ''
    for n, a in to_start:
        if n in ScheduledStart and datetime.now() < ScheduledStart[n]:
            msg += f'{n} {a} is already scheduled to start at {ScheduledStart[n].strftime("%Y-%m-%d %H:%M:%S")}\n'
            continue
        if n not in next_task_table:
            msg += f'{n} {a} has no enabled task, skipping\n'
            continue
        task, ttime = next_task_table[n]
        if ttime <= datetime.now():
            msg += f'{n} {a} will start later, task: {task}\n'
            continue
        msg += f'{n} {a} will start around {ttime.strftime("%Y-%m-%d %H:%M:%S")}, task: {task}\n'
    popup('Started', msg)
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
    global ScheduledStart
    popup('Please wait')
    ins = get_all_instance_addresses()
    msg = ''
    for name, addr in ins.items():
        alas = ProcessManager.get_manager(name)
        estd = check_connection(addr, timeout=0.1)
        msg += f'{name} {addr} {"Running" if alas.alive else "Stopped"} {"O" if estd else "X"}'
        if name in ScheduledStart and not alas.alive:
            msg += f' Scheduled at {ScheduledStart[name].strftime("%Y-%m-%d %H:%M:%S")}'
        msg += '\n'
    popup('Status', msg)

def kill_all_instances():
    help = '# List of profile instances to keep, separated by line'
    buts = textarea(
        'Exception List',
        code = {
            'mode': "markdown",
            'theme': 'darcula',
        },
        value=get_localstorage('kill_buts', help),
    )
    set_localstorage('kill_buts', buts)
    buts = [l.strip() for l in str(buts).split('\n')]
    buts = [l for l in buts if not l.startswith('#')]
    popup('Please wait')
    ins = get_all_instance_addresses()
    msg = ''
    for name, addr in ins.items():
        if name in buts:
            continue
        if kill_remote_browser(name):
            msg += f'{name} {addr}\n'
    popup('Killed', msg)
