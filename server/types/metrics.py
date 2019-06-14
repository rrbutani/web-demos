from server.types import Metrics

# TODO: add overloaded functions once we have traces and such
def into_metrics(time_to_execute: int) -> Metrics:
    return Metrics(time_to_execute=time_to_execute)
