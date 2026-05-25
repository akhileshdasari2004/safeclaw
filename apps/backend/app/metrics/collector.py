"""In-process operational metrics — no Redis required."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricsCollector:
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    gauges: dict[str, float] = field(default_factory=dict)
    histograms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def inc(self, name: str, value: int = 1) -> None:
        with self._lock:
            self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self.gauges[name] = value

    def observe(self, name: str, value: float, *, max_samples: int = 500) -> None:
        with self._lock:
            bucket = self.histograms[name]
            bucket.append(value)
            if len(bucket) > max_samples:
                del bucket[: len(bucket) - max_samples]

    def snapshot(self) -> dict:
        with self._lock:
            hist_summary = {}
            for k, vals in self.histograms.items():
                if vals:
                    hist_summary[k] = {
                        "count": len(vals),
                        "avg": sum(vals) / len(vals),
                        "max": max(vals),
                    }
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": hist_summary,
                "ts": time.time(),
            }


metrics = MetricsCollector()
