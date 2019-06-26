from server.types import Error
import traceback
import re

from server.debug import dprint, if_debug

# TODO: Switch usages of this to actually pass in Exceptions
def into_error(err: Exception) -> Error:
    # TODO: switch case the err types and map to real kinds
    # (which we'll define later, I guess)

    msg = " ".join(re.sub(r'([A-Z])', r' \1', err.__class__.__name__).split())
    msg = f"[{msg}] {err}"

    dprint(f"Returning Err: `{msg}`")
    if_debug(lambda: traceback.print_exc())

    return Error(kind=Error.Kind.OTHER, message=f"{msg}")
