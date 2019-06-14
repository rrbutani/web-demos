from server.types import Error


# TODO: Switch usages of this to actually pass in Exceptions
def into_error(err: Exception) -> Error:
    # TODO: switch case the err types and map to real kinds
    # (which we'll define later, I guess)

    return Error(kind=Error.Kind.OTHER, message=f"{err}")
