from server.types import Metrics as MetricsMessage
from __future__ import annotations

class Metrics:
    def __init__(self, time_to_execute: int = 0, trace_url: str = ""):
        self.time_to_execute(time_to_execute)
        self.trace_url(trace_url)

    def time_to_execute(self, time_to_execute: int) -> LocalMetrics:
        assert time_to_execute >= 0

        self._time_to_execute = time_to_execute
        return self

    def trace(self, trace: str) -> LocalMetrics:
        self._trace = trace
        return self

    def into_metrics(self) -> Metrics:
        return Metrics(time_to_execute=self._time_to_execute, trace=self._trace)

# # TODO: add overloaded functions once we have traces and such
# def into_metrics(metrics: LocalMetrics) -> Metrics:
#     return Metrics(time_to_execute=metrics.)
