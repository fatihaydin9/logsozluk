"""
Token Tracker Unit Tests

Tests for the token tracking and cost calculation system.
"""

import sys
import tempfile
from pathlib import Path

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from token_tracker import (
    TokenTracker, UsageRecord, get_tracker, reset_tracker,
    track_usage, estimate_cost, estimate_simulation_cost,
    format_cost_report, MODEL_PRICING
)


class TestTokenTracker:
    """Token tracker unit tests."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_tracker()

    def test_singleton_pattern(self):
        """Tracker should be a singleton."""
        tracker1 = get_tracker()
        tracker2 = get_tracker()
        assert tracker1 is tracker2

    def test_record_usage(self):
        """Should record token usage correctly."""
        tracker = get_tracker()

        record = tracker.record_usage(
            model="gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
            context="test",
            agent_name="test_agent"
        )

        assert record.model == "gpt-4o-mini"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.context == "test"
        assert record.agent_name == "test_agent"
        assert record.total_cost > 0

    def test_cost_calculation_gpt4o_mini(self):
        """Should calculate GPT-4o-mini costs correctly."""
        tracker = get_tracker()

        # 1M input tokens + 1M output tokens
        costs = tracker.calculate_cost("gpt-4o-mini", 1_000_000, 1_000_000)

        # GPT-4o-mini: $0.15/1M input, $0.60/1M output
        assert costs["input_cost"] == 0.15
        assert costs["output_cost"] == 0.60
        assert costs["total_cost"] == 0.75

    def test_cost_calculation_gpt4o(self):
        """Should calculate GPT-4o costs correctly."""
        tracker = get_tracker()

        costs = tracker.calculate_cost("gpt-4o", 1_000_000, 1_000_000)

        # GPT-4o: $2.50/1M input, $10.00/1M output
        assert costs["input_cost"] == 2.50
        assert costs["output_cost"] == 10.00
        assert costs["total_cost"] == 12.50

    def test_cost_calculation_claude(self):
        """Should calculate Claude costs correctly."""
        tracker = get_tracker()

        costs = tracker.calculate_cost("claude-3-5-sonnet-20241022", 1_000_000, 1_000_000)

        # Claude 3.5 Sonnet: $3.00/1M input, $15.00/1M output
        assert costs["input_cost"] == 3.00
        assert costs["output_cost"] == 15.00
        assert costs["total_cost"] == 18.00

    def test_cost_calculation_ollama(self):
        """Ollama should be free."""
        tracker = get_tracker()

        costs = tracker.calculate_cost("llama3.2", 1_000_000, 1_000_000)

        assert costs["input_cost"] == 0.0
        assert costs["output_cost"] == 0.0
        assert costs["total_cost"] == 0.0

    def test_report_generation(self):
        """Should generate report correctly."""
        tracker = get_tracker()

        # Add some usage
        tracker.record_usage("gpt-4o-mini", 1000, 500, "entry", "bot_a")
        tracker.record_usage("gpt-4o-mini", 800, 300, "comment", "bot_a")
        tracker.record_usage("gpt-4o", 1000, 500, "entry", "bot_b")

        report = tracker.get_report()

        # Check totals
        assert report["totals"]["calls"] == 3
        assert report["totals"]["input_tokens"] == 2800
        assert report["totals"]["output_tokens"] == 1300
        assert report["totals"]["total_cost"] > 0

        # Check by_model
        assert "gpt-4o-mini" in report["by_model"]
        assert "gpt-4o" in report["by_model"]
        assert report["by_model"]["gpt-4o-mini"]["calls"] == 2
        assert report["by_model"]["gpt-4o"]["calls"] == 1

        # Check by_agent
        assert "bot_a" in report["by_agent"]
        assert "bot_b" in report["by_agent"]
        assert report["by_agent"]["bot_a"]["calls"] == 2

        # Check by_context
        assert "entry" in report["by_context"]
        assert "comment" in report["by_context"]

    def test_summary_string(self):
        """Should generate readable summary."""
        tracker = get_tracker()

        tracker.record_usage("gpt-4o-mini", 1000, 500, "test", "test_bot")

        summary = tracker.get_summary()

        assert "TOKEN USAGE SUMMARY" in summary
        assert "Total API Calls: 1" in summary
        assert "Input Tokens:" in summary
        assert "TOTAL COST:" in summary

    def test_estimate_simulation_cost(self):
        """Should estimate simulation costs."""
        report = estimate_simulation_cost(
            num_agents=5,
            ticks_per_agent=100,
            actions_per_tick=0.5,
            avg_input_tokens=300,
            avg_output_tokens=200,
            model="gpt-4o-mini"
        )

        assert report["model"] == "gpt-4o-mini"
        assert report["estimates"]["total_actions"] == 250  # 5 * 100 * 0.5
        assert report["estimates"]["total_input_tokens"] == 75000  # 250 * 300
        assert report["estimates"]["total_output_tokens"] == 50000  # 250 * 200

    def test_format_cost_report(self):
        """Should format cost report nicely."""
        report = estimate_simulation_cost(
            num_agents=5,
            ticks_per_agent=100,
            actions_per_tick=0.5,
            model="gpt-4o-mini"
        )

        formatted = format_cost_report(report)

        assert "COST ESTIMATION REPORT" in formatted
        assert "gpt-4o-mini" in formatted
        assert "Total Actions:" in formatted
        assert "TOTAL COST:" in formatted

    def test_unknown_model_fallback(self):
        """Should use default pricing for unknown models."""
        tracker = get_tracker()

        costs = tracker.calculate_cost("unknown-model-xyz", 1_000_000, 1_000_000)

        # Default: $1.00/1M input, $3.00/1M output
        assert costs["input_cost"] == 1.00
        assert costs["output_cost"] == 3.00

    def test_reset_tracker(self):
        """Should reset all data."""
        tracker = get_tracker()

        tracker.record_usage("gpt-4o-mini", 1000, 500)
        assert tracker.session_stats.total_calls == 1

        reset_tracker()
        tracker = get_tracker()

        assert tracker.session_stats.total_calls == 0

    def test_track_usage_convenience_function(self):
        """Convenience function should work."""
        reset_tracker()

        record = track_usage(
            model="gpt-4o-mini",
            input_tokens=500,
            output_tokens=200,
            context="test"
        )

        assert record.model == "gpt-4o-mini"

        # Check it was recorded
        tracker = get_tracker()
        assert tracker.session_stats.total_calls == 1


class TestModelPricing:
    """Model pricing tests."""

    def test_all_models_have_required_fields(self):
        """All models should have input, output, provider."""
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"{model} missing input price"
            assert "output" in pricing, f"{model} missing output price"
            assert "provider" in pricing, f"{model} missing provider"

    def test_openai_models_exist(self):
        """Should have common OpenAI models."""
        assert "gpt-4o-mini" in MODEL_PRICING
        assert "gpt-4o" in MODEL_PRICING
        assert "gpt-4" in MODEL_PRICING

    def test_anthropic_models_exist(self):
        """Should have common Anthropic models."""
        assert "claude-3-5-sonnet-20241022" in MODEL_PRICING
        assert "claude-3-haiku-20240307" in MODEL_PRICING

    def test_ollama_models_free(self):
        """Ollama models should be free."""
        for model, pricing in MODEL_PRICING.items():
            if pricing["provider"] == "ollama":
                assert pricing["input"] == 0.0
                assert pricing["output"] == 0.0


class TestCostScenarios:
    """Real-world cost scenario tests."""

    def setup_method(self):
        reset_tracker()

    def test_daily_agent_cost(self):
        """Estimate daily cost for single agent."""
        # Typical agent: 12 polls/day * 5 actions avg = 60 actions
        # Each action: ~300 input, ~200 output

        actions_per_day = 60
        total_input = actions_per_day * 300
        total_output = actions_per_day * 200

        costs = estimate_cost("gpt-4o-mini", total_input, total_output)

        # Should be very cheap with gpt-4o-mini
        assert costs["total_cost"] < 0.05  # Less than 5 cents/day

    def test_monthly_16_agents_cost(self):
        """Estimate monthly cost for 16 agents."""
        # 16 agents * 60 actions/day * 30 days = 28,800 actions
        # Each action: ~350 input (avg), ~200 output (avg)

        total_actions = 16 * 60 * 30
        total_input = total_actions * 350
        total_output = total_actions * 200

        costs = estimate_cost("gpt-4o-mini", total_input, total_output)

        # With gpt-4o-mini, should be under $5/month
        print(f"\n16 agents monthly cost (gpt-4o-mini): ${costs['total_cost']:.2f}")
        assert costs["total_cost"] < 10.0  # Sanity check

        # Compare with gpt-4o
        costs_4o = estimate_cost("gpt-4o", total_input, total_output)
        print(f"16 agents monthly cost (gpt-4o): ${costs_4o['total_cost']:.2f}")

        # gpt-4o should be significantly more expensive
        assert costs_4o["total_cost"] > costs["total_cost"] * 10

    def test_simulation_3day_cost(self):
        """Estimate 3-day simulation cost."""
        # 5 agents, 288 ticks (3 days * 96 ticks), ~40% action rate

        report = estimate_simulation_cost(
            num_agents=5,
            ticks_per_agent=288,
            actions_per_tick=0.4,
            avg_input_tokens=350,
            avg_output_tokens=200,
            model="gpt-4o-mini"
        )

        print(f"\n3-day simulation cost estimate:")
        print(format_cost_report(report))

        # Parse cost from report
        cost_str = report["cost"]["total_cost"]
        cost_float = float(cost_str.replace("$", ""))

        assert cost_float < 1.0  # Should be under $1 for simulation


def test_all():
    """Run all tests."""
    import pytest
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    test_all()
