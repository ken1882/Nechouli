import asyncio
import collections
import itertools
import numpy as np
from playwright.sync_api import Locator
from lxml import etree

from module.device.env import IS_WINDOWS

from module.base.timer import Timer
from module.device.control import Control
from module.device.screenshot import Screenshot
from module.exception import (
    BrowserNotRunningError,
    GameNotRunningError,
    GameStuckError,
    GameTooManyClickError,
    RequestHumanTakeover
)
from module.logger import logger

def show_function_call():
    """
    Logs the stack trace of function calls.
    """
    import os
    import traceback
    stack = traceback.extract_stack()
    func_list = []
    for row in stack:
        filename, line_number, function_name, _ = row
        filename = os.path.basename(filename)
        func_list.append([filename, str(line_number), function_name])
    max_filename = max([len(row[0]) for row in func_list])
    max_linenum = max([len(row[1]) for row in func_list]) + 1

    def format_(file, line, func):
        file = file.rjust(max_filename, " ")
        line = f'L{line}'.rjust(max_linenum, " ")
        if not func.startswith('<'):
            func = f'{func}()'
        return f'{file} {line} {func}'

    func_list = [f'\n{format_(*row)}' for row in func_list]
    logger.info('Function calls:' + ''.join(func_list))

class Device(Control, Screenshot):
    _screen_size_checked = False
    detect_record = set()
    click_record = collections.deque(maxlen=30)
    stuck_timer = Timer(60, count=60).start()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.screenshot_interval_set()

        # Early init
        if self.config.is_actual_task:
            pass

    def run_simple_screenshot_benchmark(self):
        """
        Perform a screenshot method benchmark, test 3 times on each method.
        The fastest one will be set into config.
        """
        return

    def method_check(self):
        return True

    def screenshot(self, target:Locator=None) -> np.ndarray:
        self._screenshot_target = target
        return super().screenshot()

    def dump_hierarchy(self) -> etree._Element:
        self.stuck_record_check()
        return super().dump_hierarchy()

    def release_during_wait(self):
        return

    def get_orientation(self):
        return

    def stuck_record_add(self, button):
        self.detect_record.add(str(button))

    def stuck_record_clear(self):
        self.detect_record = set()
        self.stuck_timer.reset()

    def stuck_record_check(self):
        """
        Raises:
            GameStuckError:
        """
        reached = self.stuck_timer.reached()
        if not reached:
            return False

        show_function_call()
        logger.warning('Wait too long')
        logger.warning(f'Waiting for {self.detect_record}')
        self.stuck_record_clear()

        if self.app_is_running():
            raise GameStuckError(f'Wait too long')
        else:
            raise GameNotRunningError('Game died')

    def handle_control_check(self, button):
        self.stuck_record_clear()
        self.click_record_add(button)
        self.click_record_check()

    def click_record_add(self, button):
        self.click_record.append(str(button))

    def click_record_clear(self):
        self.click_record.clear()

    def click_record_remove(self, button):
        """
        Remove a button from `click_record`

        Args:
            button (Button):

        Returns:
            int: Number of button removed
        """
        removed = 0
        for _ in range(self.click_record.maxlen):
            try:
                self.click_record.remove(str(button))
                removed += 1
            except ValueError:
                # Value not in queue
                break

        return removed

    def click_record_check(self):
        """
        Raises:
            GameTooManyClickError:
        """
        first15 = itertools.islice(self.click_record, 0, 15)
        count = collections.Counter(first15).most_common(2)
        if count[0][1] >= 12:
            # Allow more clicks in Ruan Mei event
            if 'CHOOSE_OPTION_CONFIRM' in self.click_record and 'BLESSING_CONFIRM' in self.click_record:
                count = collections.Counter(self.click_record).most_common(2)
                if count[0][0] == 'BLESSING_CONFIRM' and count[0][1] < 25:
                    return
            show_function_call()
            logger.warning(f'Too many click for a button: {count[0][0]}')
            logger.warning(f'History click: {[str(prev) for prev in self.click_record]}')
            self.click_record_clear()
            raise GameTooManyClickError(f'Too many click for a button: {count[0][0]}')
        if len(count) >= 2 and count[0][1] >= 6 and count[1][1] >= 6:
            show_function_call()
            logger.warning(f'Too many click between 2 buttons: {count[0][0]}, {count[1][0]}')
            logger.warning(f'History click: {[str(prev) for prev in self.click_record]}')
            self.click_record_clear()
            raise GameTooManyClickError(f'Too many click between 2 buttons: {count[0][0]}, {count[1][0]}')

    def disable_stuck_detection(self):
        """
        Disable stuck detection and its handler. Usually uses in semi auto and debugging.
        """
        logger.info('Disable stuck detection')

        def empty_function(*arg, **kwargs):
            return False

        self.click_record_check = empty_function
        self.stuck_record_check = empty_function

    def app_start(self):
        super().app_start()
        self.stuck_record_clear()
        self.click_record_clear()

    def app_stop(self):
        super().app_stop()
        self.stuck_record_clear()
        self.click_record_clear()
