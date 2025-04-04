class ScriptError(Exception):
    # This is likely to be a mistake of developers, but sometimes a random issue
    pass


class GameStuckError(Exception):
    pass


class GameBugError(Exception):
    # An error has occurred in Azur Lane game client. Alas is unable to handle.
    # A restart should fix it.
    pass


class GameTooManyClickError(Exception):
    pass


class HandledError(Exception):
    # Error handled before raising
    # No extra handling required, just retry
    pass


class EmulatorNotRunningError(Exception):
    pass

class BrowserNotRunningError(Exception):
    pass

class GameNotRunningError(Exception):
    pass


class GamePageUnknownError(Exception):
    pass


class TaskError(Exception):
    # An error occurred in task,
    # task itself should have error handled before raising TaskError,
    # then task will be re-scheduled
    pass


class RequestHumanTakeover(Exception):
    # Request human takeover
    # Alas is unable to handle such error, probably because of wrong settings.
    pass

class InvisibleElement(Exception):
    # Raised when attempt to perform action on an invisible element
    pass