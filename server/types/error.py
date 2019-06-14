from server.types import Error
import traceback

# TODO: Switch usages of this to actually pass in Exceptions
def into_error(err: Exception) -> Error:
    # TODO: switch case the err types and map to real kinds
    # (which we'll define later, I guess)

    # TODO: make this only print out if the debug environment variable is set:
    print(f"Returning Err: {err}")
    traceback.print_exc()

    return Error(kind=Error.Kind.OTHER, message=f"{err}")
