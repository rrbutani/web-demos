from __future__ import annotations

from typing import Union, Optional

from ..types import Metrics as MetricsMessage


class Metrics:
    def __init__(self, time_to_execute: int = 0, trace_url: str = ""):
        self._trace_url: Optional[str]
        self._time_to_execute: Optional[int]

        self.time_to_execute(time_to_execute)
        self.trace(trace_url)

    def time_to_execute(self, time_to_execute: Union[int, float]) -> Metrics:
        assert time_to_execute >= 0

        self._time_to_execute = int(time_to_execute)
        return self

    def trace(self, trace_url: str) -> Metrics:
        self._trace_url = trace_url
        return self

    def into(self) -> MetricsMessage:
        mm = MetricsMessage()

        if self._time_to_execute:
            mm.time_to_execute = self._time_to_execute

        if self._trace_url:
            mm.trace_url = self._trace_url

        return mm
