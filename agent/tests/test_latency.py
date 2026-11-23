import pytest

from babakoto_agent.latency import TurnLatency, percentile, turn_latency


def test_turn_latency_reads_assistant_metrics() -> None:
    result = turn_latency({"e2e_latency": 1.2, "llm_node_ttft": 0.4, "tts_node_ttfb": 0.5})
    assert result == TurnLatency(e2e=1.2, llm_ttft=0.4, tts_ttfb=0.5)
    assert result.to_json() == {"e2e": 1.2, "llm_ttft": 0.4, "tts_ttfb": 0.5}


def test_missing_optional_stages_are_none() -> None:
    assert turn_latency({"e2e_latency": 0.9}) == TurnLatency(0.9, None, None)


@pytest.mark.parametrize("metrics", [None, {}, {"llm_node_ttft": 0.4}])
def test_interrupted_or_empty_turns_have_no_latency(metrics: dict[str, float] | None) -> None:
    assert turn_latency(metrics) is None


def test_percentile() -> None:
    values = [float(v) for v in range(1, 101)]
    assert percentile(values, 50) == pytest.approx(50.5)
    assert percentile(values, 95) == pytest.approx(95.05)
    assert percentile([2.0], 95) == 2.0
    assert percentile([3.0, 1.0], 0) == 1.0
    with pytest.raises(ValueError, match="no values"):
        percentile([], 50)
