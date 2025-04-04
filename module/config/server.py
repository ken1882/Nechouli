"""
This file stores server, such as 'cn', 'en'.
Use 'import module.config.server as server' to import, don't use 'from xxx import xxx'.
"""
lang = 'en'  # Setting default to cn, will avoid errors when using dev_tools
server = 'EN-Official'

VALID_LANG = ['en']
VALID_SERVER = {
    'EN-Official': 'www.neopets.com',
}
VALID_PACKAGE = set(list(VALID_SERVER.values()))
VALID_CLOUD_SERVER = {}
VALID_CLOUD_PACKAGE = set(list(VALID_CLOUD_SERVER.values()))

DICT_PACKAGE_TO_ACTIVITY = {}


def set_lang(lang_: str):
    """
    Change language and this will affect globally,
    including assets and language specific methods.

    Args:
        lang_: package name or server.
    """
    global lang
    lang = lang_

    from module.base.resource import release_resources
    release_resources()


def to_server(package_or_server: str) -> str:
    """
    Convert package/server to server.
    To unknown packages, consider they are a CN channel servers.
    """
    for key, value in VALID_SERVER.items():
        if value == package_or_server:
            return key
        if key == package_or_server:
            return key
    for key, value in VALID_CLOUD_SERVER.items():
        if value == package_or_server:
            return key
        if key == package_or_server:
            return key

    raise ValueError(f'Package invalid: {package_or_server}')


def to_package(package_or_server: str, is_cloud=False) -> str:
    """
    Convert package/server to package.
    """
    if is_cloud:
        for key, value in VALID_CLOUD_SERVER.items():
            if value == package_or_server:
                return value
            if key == package_or_server:
                return value
    else:
        for key, value in VALID_SERVER.items():
            if value == package_or_server:
                return value
            if key == package_or_server:
                return value

    raise ValueError(f'Server invalid: {package_or_server}')
