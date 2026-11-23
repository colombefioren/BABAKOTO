"""Per-turn latency from LiveKit's chat message metrics."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

TOPIC = "babakoto.latency"


@dataclass(frozen=True)
class TurnLatency:
    """Seconds spent in each stage of one agent reply."""

    # End of user speech to first agent audio. This is the number the milestone targets.
    e2e: float
    llm_ttft: float | None
    tts_ttfb: float | None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def turn_latency(metrics: Mapping[str, Any] | None) -> TurnLatency | None:
    """Read latency from an assistant message's metrics; None when the turn has no e2e number.

    A turn that was interrupted before any audio plays has no `e2e_latency`.
    """
    if not metrics or "e2e_latency" not in metrics:
        return None
    return TurnLatency(
        e2e=float(metrics["e2e_latency"]),
        llm_ttft=_optional(metrics, "llm_node_ttft"),
        tts_ttfb=_optional(metrics, "tts_node_ttfb"),
    )


def _optional(metrics: Mapping[str, Any], key: str) -> float | None:
    return float(metrics[key]) if key in metrics else None


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile (q in 0..100) of a non-empty list."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    rank = (len(ordered) - 1) * q / 100
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)
