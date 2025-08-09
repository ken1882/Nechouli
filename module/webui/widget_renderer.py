from pywebio.output import *
from pywebio.io_ctrl import Output
from typing import TYPE_CHECKING, Dict, Union, Any

if TYPE_CHECKING:
    from module.db.models.neoitem import NeoItem

T_Output_Kwargs = Dict[str, Union[str, Dict[str, Any]]]

def get_title_help(kwargs):
    title: str = kwargs.get("title", "")
    help_text: str = kwargs.get("help", "")
    name: str = kwargs.get("name", "")
    if help_text:
        html = f'''
        <div style="display: flex; flex-direction: column; gap: 0.25em;">
            <div style="--arg-title--" id="_args-title_{name}">{title}</div>
            <div style="--arg-help--" id="_args-help_{name}">{help_text}</div>
        </div>
        '''
    else:
        html = f'''
        <div>
            <div style="--arg-title--" id="_args-title_{name}">{title}</div>
        </div>
        '''
    return put_html(html)


def handle_inventory(kwargs):
    name = kwargs["name"]
    rows = []
    data = kwargs.get('value', {})
    items: list['NeoItem'] = data.get('items', [])
    put_html('''
    <script>
        function changeSelectedItem_%s(name, type){
            n = document.getElementById("_args-title_%s");
            if (name){
                n.textContent = n.textContent.split(":")[0] + ": " + name;
            }
            else {
                n.textContent = n.textContent.split(":")[0];
            }
        }
    </script>
    ''' % (name, name))
    html = "<div>"
    tmp = ''
    for item in items:
        text = item.name
        if name.endswith('StockData'):
            text += f" (has {item.quantity} stocked selling for {item.stocked_price} NP)"
        content = f'''
        <div class="neoitem" onmouseover="changeSelectedItem_{name}('{text}')" onmouseleave="changeSelectedItem_{name}('')">
            <img src="{item.image}" alt="{item.name}">
        </div>
        '''
        if item.category == 'cash':
            tmp += content
            continue
        html += content
    if tmp:
        html += '<hr>\n'+tmp
    html += "</div>"
    rows.append(put_html(html))
    return put_scope(
        f"arg_container-stored-{name}",
        [
            get_title_help(kwargs),
            put_scope(
                f"arg_stored-stored-value-{name}",
                rows,
            )
        ]
    )


HANDLE_TABLE = {
    "InventoryTool_PlayerStorage_InventoryData": handle_inventory,
    "InventoryTool_PlayerStorage_StockData": handle_inventory,
}

def can_handle(name: str) -> bool:
    return name in HANDLE_TABLE

def render(name, kwargs):
    return HANDLE_TABLE[name](kwargs)