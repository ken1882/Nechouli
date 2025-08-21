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
from module.webui.process_manager import ProcessManager
from module.webui.updater import updater
from module.base.utils import (
    str2int,
    kill_remote_browser,
    check_connection,
    get_all_instance_addresses
)

def run_all_instances():
    popup('Please wait')
    ins = get_all_instance_addresses()
    msg = ''
    for name, addr in ins.items():
        alas = ProcessManager.get_manager(name)
        if alas.alive:
            continue
        alas.start(None, updater.event)
        msg += f'{name} {addr}\n'
    popup('Started', msg)

def stop_all_instances():
    popup('Please wait')
    ins = get_all_instance_addresses()
    msg = ''
    for name, addr in ins.items():
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
