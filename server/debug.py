import os
import sys
from typing import Any, Callable, TypeVar, Optional

_DEBUG = "DEBUG" in os.environ

def dprint(*args: Any, **kwargs: Any) -> None:
    if _DEBUG:
        kwargs['file'] = sys.stderr
        print(*args, **kwargs)

T = TypeVar('T')
def if_debug(func: Callable[[], T]) -> Optional[T]:
    if _DEBUG:
        return func()
    else:
        return None


dprint(
    "\n**************************** Debug logging enabled! ****************************\n"
)
