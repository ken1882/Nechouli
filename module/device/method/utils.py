import os
import random
import re
import socket
import time
import typing as t
from lxml import etree
from module.base.decorator import cached_property
from module.logger import logger

RETRY_TRIES = 5
RETRY_DELAY = 3


def is_port_using(port_num):
    """ if port is using by others, return True. else return False """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)

    try:
        s.bind(('127.0.0.1', port_num))
        return False
    except OSError:
        # Address already bind
        return True
    finally:
        s.close()


def random_port(port_range):
    """ get a random port from port set """
    new_port = random.choice(list(range(*port_range)))
    if is_port_using(new_port):
        return random_port(port_range)
    else:
        return new_port

def possible_reasons(*args):
    """
    Show possible reasons

        Possible reason #1: <reason_1>
        Possible reason #2: <reason_2>
    """
    for index, reason in enumerate(args):
        index += 1
        logger.critical(f'Possible reason #{index}: {reason}')


class PackageNotInstalled(Exception):
    pass


class ImageTruncated(Exception):
    pass


def retry_sleep(trial):
    # First trial
    if trial == 0:
        return 0
    # Failed once, fast retry
    elif trial == 1:
        return 0
    # Failed twice
    elif trial == 2:
        return 1
    # Failed more
    else:
        return RETRY_DELAY

def handle_unknown_host_service(e):
    """
    Args:
        e (Exception):

    Returns:
        bool: If should retry
    """
    text = str(e)
    if 'unknown host service' in text:
        # AdbError(unknown host service)
        # Another version of ADB service started, current ADB service has been killed.
        # Usually because user opened a Chinese emulator, which uses ADB from the Stone Age.
        logger.error(e)
        return True
    else:
        return False


def remove_prefix(s, prefix):
    """
    Remove prefix of a string or bytes like `string.removeprefix(prefix)`, which is on Python3.9+

    Args:
        s (str, bytes):
        prefix (str, bytes):

    Returns:
        str, bytes:
    """
    return s[len(prefix):] if s.startswith(prefix) else s


def remove_suffix(s, suffix):
    """
    Remove suffix of a string or bytes like `string.removesuffix(suffix)`, which is on Python3.9+

    Args:
        s (str, bytes):
        suffix (str, bytes):

    Returns:
        str, bytes:
    """
    return s[:-len(suffix)] if s.endswith(suffix) else s


class HierarchyButton:
    """
    Convert UI hierarchy to an object like the Button in Alas.
    """
    _name_regex = re.compile('@.*?=[\'\"](.*?)[\'\"]')

    def __init__(self, hierarchy: etree._Element, xpath: str):
        self.hierarchy = hierarchy
        self.xpath = xpath
        self.nodes = hierarchy.xpath(xpath)

    @cached_property
    def name(self):
        res = HierarchyButton._name_regex.findall(self.xpath)
        if res:
            return res[0]
        else:
            return self.xpath

    @cached_property
    def count(self):
        return len(self.nodes)

    @cached_property
    def exist(self):
        return self.count == 1

    @cached_property
    def attrib(self):
        if self.exist:
            return self.nodes[0].attrib
        else:
            return {}

    @cached_property
    def area(self):
        if self.exist:
            bounds = self.attrib.get("bounds")
            lx, ly, rx, ry = map(int, re.findall(r"\d+", bounds))
            return lx, ly, rx, ry
        else:
            return None

    @cached_property
    def size(self):
        if self.area is not None:
            lx, ly, rx, ry = self.area
            return rx - lx, ry - ly
        else:
            return None

    @cached_property
    def button(self):
        return self.area

    def __bool__(self):
        return self.exist

    def __str__(self):
        return self.name

    """
    Element props
    """

    def _get_bool_prop(self, prop: str) -> bool:
        return self.attrib.get(prop, "").lower() == 'true'

    @cached_property
    def index(self) -> int:
        try:
            return int(self.attrib.get("index", 0))
        except IndexError:
            return 0

    @cached_property
    def text(self) -> str:
        return self.attrib.get("text", "").strip()

    @cached_property
    def resourceId(self) -> str:
        return self.attrib.get("resourceId", "").strip()

    @cached_property
    def package(self) -> str:
        return self.attrib.get("resourceId", "").strip()

    @cached_property
    def description(self) -> str:
        return self.attrib.get("resourceId", "").strip()

    @cached_property
    def checkable(self) -> bool:
        return self._get_bool_prop('checkable')

    @cached_property
    def clickable(self) -> bool:
        return self._get_bool_prop('clickable')

    @cached_property
    def enabled(self) -> bool:
        return self._get_bool_prop('enabled')

    @cached_property
    def fucusable(self) -> bool:
        return self._get_bool_prop('fucusable')

    @cached_property
    def focused(self) -> bool:
        return self._get_bool_prop('focused')

    @cached_property
    def scrollable(self) -> bool:
        return self._get_bool_prop('scrollable')

    @cached_property
    def longClickable(self) -> bool:
        return self._get_bool_prop('longClickable')

    @cached_property
    def password(self) -> bool:
        return self._get_bool_prop('password')

    @cached_property
    def selected(self) -> bool:
        return self._get_bool_prop('selected')


class AreaButton:
    def __init__(self, area, name='AREA_BUTTON'):
        self.area = area
        self.color = ()
        self.name = name
        self.button = area

    def __str__(self):
        return self.name

    def __bool__(self):
        # Cannot appear
        return False
