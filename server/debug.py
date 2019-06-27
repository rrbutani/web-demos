import os

_DEBUG = "DEBUG" in os.environ


def dprint(*args, **kwargs):
    if _DEBUG:
        print(*args, **kwargs)


def if_debug(func):
    if _DEBUG:
        func()


dprint(
    "\n**************************** Debug logging enabled! ****************************\n"
)
