from turtle import st
from pywebio.output import *
from pywebio.session import run_js
from pywebio.io_ctrl import Output
from module.webui.lang import _t, t
from typing import TYPE_CHECKING, Dict, Union, Any
from datetime import datetime

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
    items: list['NeoItem'] = data.get('value', [])
    html = "<div>"
    tmp = ''
    for item in items:
        text = item.name
        if name.endswith('StockData'):
            text += f" (has {item.quantity} stocked selling for {item.stocked_price} NP)"
        content = f'''
        <div class="neoitem" onmouseover="{generate_item_info_script(item)}">
            <img src="{item.image}" alt="{item.name}" onclick="selectItem(event)">
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

@use_scope("navigator")
def put_item_info_box(_):
    put_html(f'''
    <div class="infobox" id="item-info-box" style="display: none;">
        <div id="item_info_title">{t("Gui.ItemInfo.Title")}</div>
        <div id="item_info_image" style="width: 80px; height: 80px; text-align: center;">
        </div>
        <div>
            <span>{t("Gui.ItemInfo.Name")}:</span>
            <p id="item_info_name"></p>
        </div>
        <div>
            <span>{t("Gui.ItemInfo.Description")}:</span>
            <p id="item_info_description"></p>
        </div>
        <div id="item_info_quantity_container">
            <span>{t("Gui.ItemInfo.Quantity")}:</span>
            <p id="item_info_quantity"></p>
        </div>
        <div>
            <span>{t("Gui.ItemInfo.Type")}:</span>
            <p id="item_info_type"></p>
        </div>
        <div style="display: none;"> <!-- Hidden due to useless -->
            <span>{t("Gui.ItemInfo.Rarity")}:</span>
            <p id="item_info_rarity"></p>
        </div>
        <div>
            <span>{t("Gui.ItemInfo.MarketPrice")}:</span>
            <p id="item_info_market_price"></p>
        </div>
        <div>
            <span>{t("Gui.ItemInfo.PriceDate")}:</span>
            <p id="item_info_price_date"></p>
        </div>
        <div id="item_info_stocked_price_container">
            <span>{t("Gui.ItemInfo.StockedPrice")}:</span>
            <p id="item_info_stocked_price"></p>
        </div>
        <div>
            <span>{t("Gui.ItemInfo.JellyNeoLink")}:</span>
            <p id="item_info_jellyneo_link"></p>
        </div>
    </div>
    ''')
    put_html('''
    <script>
        function changeItemInfo(i,n,d,q,t,r,mp,pd,sp,jl){
            if(window._selectedItem){ return; }
            document.getElementById("item-info-box").style.display = "block";
            document.getElementById("item_info_image").innerHTML = `<img src="${i}" alt="${n}">`;
            document.getElementById("item_info_name").textContent = n;
            document.getElementById("item_info_description").textContent = d;
            document.getElementById("item_info_quantity").textContent = q;
            document.getElementById("item_info_type").textContent = t;
            document.getElementById("item_info_rarity").textContent = r;
            document.getElementById("item_info_market_price").textContent = mp;
            document.getElementById("item_info_price_date").textContent = pd;
            document.getElementById("item_info_stocked_price").textContent = sp;
            document.getElementById("item_info_jellyneo_link").innerHTML = `<a href="${jl}" target="_blank">${jl}</a>`;
            if (q > 0) {
                document.getElementById("item_info_quantity_container").style.display = "block";
            } else {
                document.getElementById("item_info_quantity_container").style.display = "none";
            }
            if (sp > 0) {
                document.getElementById("item_info_stocked_price_container").style.display = "block";
            } else {
                document.getElementById("item_info_stocked_price_container").style.display = "none";
            }
        }

        function selectItem(e) {
            p = window._selectedItem;
            if (p) {
                p.parentElement.classList.remove('selected');
                if (p == e.target) {
                    e.target.parentElement.classList.remove('selected');
                    window._selectedItem = null;
                    return;
                }
            }
            e.target.parentElement.classList.add('selected');
            window._selectedItem = null;
            e.target.parentElement.onmouseover();
            window._selectedItem = e.target;
        }
    </script>
    ''')

def generate_item_info_script(item: 'NeoItem'):
    return f'''
    changeItemInfo(
        '{item.image}',
        '{item.name}',
        '{item.description}',
        {item.quantity},
        '{item.item_type}',
        {item.rarity},
        {item.market_price},
        '{datetime.fromtimestamp(int(item.price_timestamp)).strftime("%Y-%m-%d %H:%M:%S")}',
        {getattr(item, "stocked_price", 0)},
        'https://items.jellyneo.net/item/{item.id}'
    );
    '''

def handle_deposit(kwargs):
    try:
        kwargs['value']['value'] = sorted(kwargs['value']['value'], key=lambda x: x.market_price, reverse=True)
    except KeyError:
        pass
    return handle_inventory(kwargs)

def _render_object(obj: Any) -> str:
    if getattr(obj, 'name', None):
        return obj.name
    return str(obj)

def handle_list(kwargs, value: list):
    name = kwargs["name"]
    html = "<ol>"
    for v in value:
        html += f'''
        <li>{_render_object(v)}</li>
        '''
    html += "</ol>"
    return put_scope(
        f"arg_container-stored-list-{name}",
        [
            get_title_help(kwargs),
            put_scope(
                f"arg_stored-stored-value-{name}",
                [put_html(html)],
            )
        ]
    )

HANDLE_TABLE = {
    "InventoryTool_PlayerStorage_InventoryData": handle_inventory,
    "InventoryTool_PlayerStorage_StockData": handle_inventory,
    "SafetyDepositBox_SafetyDepositBox_DepositData": handle_deposit,
}

NAVIGATOR_OVERRIDE = {
    "InventoryTool": put_item_info_box,
    "SafetyDepositBox": put_item_info_box,
}

def can_handle(name: str) -> bool:
    return name in HANDLE_TABLE

def render(name, kwargs):
    return HANDLE_TABLE[name](kwargs)