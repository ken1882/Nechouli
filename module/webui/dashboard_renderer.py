from pywebio.output import *
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from module.db.models.neoitem import NeoItem


def handle_item_container(kwargs, stored):
    return [
        put_text(len(stored.get("items", []))).style("--dashboard-value--"),
        put_text(f' / {stored.get("capacity", "0")}').style("--dashboard-time--"),
    ]

HANDLE_TABLE = {
    'StockData': handle_item_container,
    'InventoryData': handle_item_container,
}

def can_handle(name: str) -> bool:
    return name in HANDLE_TABLE

def render(kwargs, stored):
    return HANDLE_TABLE[kwargs['name']](kwargs, stored)
