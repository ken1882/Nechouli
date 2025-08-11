from datetime import datetime
from functools import cached_property as functools_cached_property

from module.base.decorator import cached_property
from module.config.utils import DEFAULT_TIME, deep_get, _recursively_convert
from module.exception import ScriptError
from typing import TYPE_CHECKING
from ast import literal_eval

if TYPE_CHECKING:
    from module.db.models.neoitem import NeoItem
    from module.config.config import AzurLaneConfig

def now():
    return datetime.now().replace(microsecond=0)


def iter_attribute(cls):
    """
    Args:
        cls: Class or object

    Yields:
        str, obj: Attribute name, attribute value
    """
    for attr in dir(cls):
        if attr.startswith('_'):
            continue
        value = getattr(cls, attr)
        if type(value).__name__ in ['function', 'property']:
            continue
        yield attr, value

class StoredBase:
    time = DEFAULT_TIME
    _config: 'AzurLaneConfig'

    def __init__(self, key):
        self._key = key
        self._config = None

    @cached_property
    def _name(self):
        return self._key.split('.')[-1]

    def _bind(self, config):
        """
        Args:
            config (AzurLaneConfig):
        """
        self._config = config

    @functools_cached_property
    def _stored(self):
        assert self._config is not None, 'StoredBase._bind() must be called before getting stored data'
        from module.logger import logger

        out = {}
        stored = deep_get(self._config.data, keys=self._key, default={})
        for attr, default in self._attrs.items():
            value = stored.get(attr, default)
            if attr == 'time':
                if not isinstance(value, datetime):
                    try:
                        value = datetime.fromisoformat(value)
                    except ValueError:
                        logger.warning(f'{self._name} has invalid attr: {attr}={value}, use default={default}')
                        value = default
            else:
                value = _recursively_convert(value, False)
                if not isinstance(value, type(default)):
                    value = literal_eval(value) if isinstance(value, str) else value
                    if not isinstance(value, type(default)):
                        logger.warning(f'{self._name} has invalid attr: {attr}={value}, use default={default}')
                        value = default

            out[attr] = value
        return out

    @cached_property
    def _attrs(self) -> dict:
        """
        All attributes defined
        """
        attrs = {
            # time is the first one
            'time': DEFAULT_TIME
        }
        for attr, value in iter_attribute(self.__class__):
            if attr.islower():
                attrs[attr] = value
        return attrs

    def __setattr__(self, key, value):
        if key in self._attrs:
            stored = self._stored
            stored['time'] = now()
            stored[key] = value
            self._config.modified[self._key] = stored
            if self._config.auto_update:
                self._config.update()
        else:
            super().__setattr__(key, value)

    def __getattribute__(self, item):
        if not item.startswith('_') and item in self._attrs:
            return self._stored[item]
        else:
            return super().__getattribute__(item)

    def is_expired(self) -> bool:
        return False

    def show(self):
        """
        Log self
        """
        from module.logger import logger
        logger.attr(self._name, self._stored)


class StoredInt(StoredBase):
    value = 0

    def clear(self):
        self.value = 0


class StoredCounter(StoredBase):
    value = 0
    total = 0

    FIXED_TOTAL = 0

    def set(self, value, total=0):
        if self.FIXED_TOTAL:
            total = self.FIXED_TOTAL
        with self._config.multi_set():
            self.value = value
            self.total = total

    def clear(self):
        self.value = 0

    def to_counter(self) -> str:
        return f'{self.value}/{self.total}'

    def is_full(self) -> bool:
        return self.value >= self.total

    def get_remain(self) -> int:
        return self.total - self.value

    def add(self, value=1):
        self.value += value

    def sub(self, value=1):
        self.value -= value
        if self.value < 0:
            self.value = 0

    @cached_property
    def _attrs(self) -> dict:
        attrs = super()._attrs
        if self.FIXED_TOTAL:
            attrs['total'] = self.FIXED_TOTAL
        return attrs

    @functools_cached_property
    def _stored(self):
        stored = super()._stored
        if self.FIXED_TOTAL:
            stored['total'] = self.FIXED_TOTAL
        return stored

class StoredDailyQuestRestockCounter(StoredCounter):
    FIXED_TOTAL = 3

class StoredDailyQuestFeedCounter(StoredCounter):
    FIXED_TOTAL = 1

class StoredItemContainer(StoredCounter):
    items: list['NeoItem'] = []
    np: int = 0
    capacity: int = 50

    def set(self, items: list['NeoItem']):
        if any(type(i).__name__ != 'NeoItem' for i in items):
            raise ScriptError(f'Unsupported item type in {self._name} for container')
        self.items = items

    def add(self, *items: 'NeoItem'):
        items = list(items)
        if any(type(i).__name__ != 'NeoItem' for i in items):
            raise ScriptError(f'Unsupported item type in {self._name} for container')
        self.items = self.items + list(items)

    def normal_items(self) -> list['NeoItem']:
        return [i for i in self.items if i.category != 'cash']

    @property
    def size(self) -> int:
        return len([i for i in self.items if i.category != 'cash'])

    def is_full(self, keeps: int = 0) -> bool:
        return self.size + keeps >= self.capacity

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.items[item]
        elif isinstance(item, str):
            for i in self.items:
                if i.name == item:
                    return i
            raise KeyError(f'Item {item} not found in {self._name}')
        else:
            raise TypeError(f'Unsupported item type: {type(item)} for {self._name}')

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if type(value).__name__ != 'NeoItem':
                raise ScriptError(f'Unsupported item type in {self._name} for container')
            self.items[key] = value
        else:
            raise TypeError(f'Unsupported item type: {type(key)} for {self._name}')

    def __contains__(self, item):
        if isinstance(item, str):
            return any(i.name == item for i in self.items)
        elif type(item).__name__ == 'NeoItem':
            return item in self.items
        else:
            raise TypeError(f'Unsupported item type: {type(item)} for {self._name}')

    def __len__(self):
        return len(self.items)

    def __bool__(self):
        return bool(self.items)

class StoredShopWizardRequests(StoredBase):
    requests: list[str] = []

    def add(self, item_name: str, source: str):
        self.requests.append(f'{item_name}@{source}')

    def clear(self):
        self.requests = []

    def pop(self) -> str:
        """
        Returns:
            str: The first request in the list, or an empty string if the list is empty.
        """
        if not self.requests:
            return ''
        return self.requests.pop(0)

    def is_empty(self) -> bool:
        return not self.requests

    def __iter__(self):
        return iter(self.requests)

    def __getitem__(self, item):
        return self.requests[item]

    def __len__(self):
        return len(self.requests)

    def __bool__(self):
        return bool(self.requests)