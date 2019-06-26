from server.types import Error
import traceback
import re

# TODO: Switch usages of this to actually pass in Exceptions
def into_error(err: Exception) -> Error:
    # TODO: switch case the err types and map to real kinds
    # (which we'll define later, I guess)

    msg = " ".join(re.sub(r'([A-Z])', r' \1', err.__class__.__name__).split())
    msg = f"[{msg}] {err}"

    # TODO: make this only print out if the debug environment variable is set:
    print(f"Returning Err: `{msg}`")
    traceback.print_exc()

    return Error(kind=Error.Kind.OTHER, message=f"{msg}")
