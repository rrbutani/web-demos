from __future__ import annotations
from typing import Union
from server.types import Metrics as MetricsMessage


class Metrics:
    def __init__(self, time_to_execute: int = 0, trace_url: str = ""):
        self.time_to_execute(time_to_execute)
        self.trace(trace_url)

    def time_to_execute(self, time_to_execute: Union[int, float]) -> Metrics:
        assert time_to_execute >= 0

        self._time_to_execute = int(time_to_execute)
        return self

    def trace(self, trace: str) -> Metrics:
        self._trace = trace
        return self

    def into(self) -> MetricsMessage:
        mm = MetricsMessage()

        if self._time_to_execute:
            mm.time_to_execute = self._time_to_execute

        if self._trace:
            mm.trace = self._trace

        return mm
