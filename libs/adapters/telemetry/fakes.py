from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from ports.telemetry import MetricsPort, TelemetryPort


@runtime_checkable
class _ModelDumpLike(Protocol):
    def model_dump(self) -> Mapping[str, Any]: ...


class FakeTelemetryPort(TelemetryPort):
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def publish(self, record: Any) -> None:
        # Accept Pydantic models (v2) or plain mappings.
        if isinstance(record, Mapping):
            self.records.append(dict(record))
        elif isinstance(record, _ModelDumpLike):
            self.records.append(dict(record.model_dump()))
        else:
            raise TypeError(
                "FakeTelemetryPort.publish expects a Mapping or an object with model_dump(). "
                f"Got: {type(record)!r}"
            )


class FakeMetricsPort(MetricsPort):
    def __init__(self) -> None:
        self.samples: list[tuple[str, float, dict[str, str]]] = []

    def observe(self, name: str, value: float, **labels: str) -> None:
        self.samples.append((name, float(value), labels))
