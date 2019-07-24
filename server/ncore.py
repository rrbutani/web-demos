import os
import stat
import sys
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar

import tensorflow as tf

from .debug import dprint

NCORE_PATH: str = "/dev/ncore_pci"

_NCORE: Optional[bool] = None
_DELEGATE_LIB_PATH: Optional[str] = None


class InvalidDelegateLibrary(Exception):
    ...


class NCoreNotPresent(Exception):
    ...


def check_for_ncore() -> Tuple[bool, Optional[str]]:
    """
    :raises InvalidDelegateLibrary: On invalid delegate shared objects.
    :raises NCoreNotPresent: When NCORE is set, but NCore is not present.
    """
    if "NCORE" in os.environ:
        # Verify that NCore is present and is a block device:
        exists = os.path.exists(NCORE_PATH)
        block_device = stat.S_ISBLK(os.stat(NCORE_PATH).st_mode)

        if exists and block_device:
            # Now check for the the library
            lib_path = os.environ["NCORE"]

            if not (os.path.exists(lib_path) and os.path.isfile(lib_path)):
                raise InvalidDelegateLibrary(f"`{lib_path}` doesn't seem to exist.")

            if os.path.splitext(lib_path)[1] != ".so":
                raise InvalidDelegateLibrary(
                    f"`{lib_path}` doesn't appear to be a shared object."
                )

            return True, lib_path

        # If it wasn't but NCORE was set, error:
        else:
            raise NCoreNotPresent(
                f"`{NCORE_PATH}`:: exists: {exists}, block device: {block_device}."
            )
    else:
        return False, None


if _NCORE is None:
    _NCORE, _DELEGATE_LIB_PATH = check_for_ncore()

present: bool = _NCORE

T = TypeVar("T")


def if_ncore(func: Callable[[], None]) -> Optional[T]:
    if _NCORE:
        return func()
    else:
        return None


def delegate_lib_path() -> Optional[str]:
    return _DELEGATE_LIB_PATH


def get_ncore_delegate_instance(
    options: Any = None
) -> Optional[List[tf.lite.Delegate]]:
    if _NCORE and _DELEGATE_LIB_PATH is not None:
        try:
            dprint("Making a new NCore delegate!")
            return [
                tf.lite.experimental.load_delegate(_DELEGATE_LIB_PATH, options=options)
            ]
        except ValueError as e:
            raise InvalidDelegateLibrary(
                f"Error while loading `{_DELEGATE_LIB_PATH}`: {e}"
            )
    else:
        return None


if_ncore(
    lambda: print(
        "\n****************************** Running on NCore!! ******************************\n"
    )
)

# try:
#     tf.lite.experimental.load_delegate()

# except ValueError as e:
#     raise InvalidDelegateLibrary(f"Error while loading `{lib_path}`: {e}")


# TODO:
#   - import this from model_store
#   - on every new model load, run this:
#     ```
#     delegates = if_ncore(get_ncore_delegate_instance) # Or: if_ncore(lambda: get_ncore_delegate_instance(options={}))
#     Interpreter(..., experimental_delegates=delegates)
#     ```
#
