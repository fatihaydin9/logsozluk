"""
Token Tracker for Logsozluk Agents

Tracks token usage across all LLM calls and calculates costs.
Singleton pattern ensures global tracking.

Usage:
    from token_tracker import get_tracker, track_usage

    # Manual tracking
    tracker = get_tracker()
    tracker.record_usage("gpt-4o-mini", 300, 200)

    # Get report
    report = tracker.get_report()
    print(f"Total cost: ${report['total_cost']:.4f}")
"""

import json
import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ============ 2026 Pricing (per 1M tokens) ============
# Updated: February 2026

MODEL_PRICING = {
    # OpenAI Models - GPT-4.1 Series (2026)
    "gpt-4.1": {"input": 3.00, "output": 12.00, "provider": "openai"},
    "gpt-4.1-mini": {"input": 0.80, "output": 3.20, "provider": "openai"},
    "gpt-4.1-nano": {"input": 0.20, "output": 0.80, "provider": "openai"},
    "o4-mini": {"input": 4.00, "output": 16.00, "provider": "openai"},

    # OpenAI Models - Legacy (still available)
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "provider": "openai"},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60, "provider": "openai"},
    "gpt-4o": {"input": 2.50, "output": 10.00, "provider": "openai"},
    "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00, "provider": "openai"},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "provider": "openai"},
    "gpt-4": {"input": 30.00, "output": 60.00, "provider": "openai"},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "provider": "openai"},

    # Anthropic Models - Claude 4.x Series (2026)
    "claude-opus-4.5": {"input": 5.00, "output": 25.00, "provider": "anthropic"},
    "claude-opus-4.1": {"input": 15.00, "output": 75.00, "provider": "anthropic"},
    "claude-opus-4": {"input": 15.00, "output": 75.00, "provider": "anthropic"},
    "claude-sonnet-4.5": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    "claude-haiku-4.5": {"input": 1.00, "output": 5.00, "provider": "anthropic"},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.00, "provider": "anthropic"},
    "claude-haiku-3": {"input": 0.25, "output": 1.25, "provider": "anthropic"},

    # Anthropic Models - Legacy (still available)
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    "claude-3-5-sonnet-latest": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00, "provider": "anthropic"},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25, "provider": "anthropic"},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00, "provider": "anthropic"},

    # Ollama / Local (free)
    "llama3.2": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "llama3.1": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "mistral": {"input": 0.0, "output": 0.0, "provider": "ollama"},
    "mixtral": {"input": 0.0, "output": 0.0, "provider": "ollama"},
}

# Default pricing for unknown models
DEFAULT_PRICING = {"input": 1.00, "output": 3.00, "provider": "unknown"}


@dataclass
class UsageRecord:
    """Tek bir API çağrısının kullanım kaydı."""
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    context: Optional[str] = None  # e.g., "entry_generation", "comment", "reflection"
    agent_name: Optional[str] = None


@dataclass
class SessionStats:
    """Oturum istatistikleri."""
    start_time: str
    end_time: Optional[str] = None
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_agent: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_context: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class TokenTracker:
    """
    Global token usage tracker (singleton).

    Thread-safe tracking of all LLM API calls.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, storage_dir: Optional[Path] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self, storage_dir: Optional[Path] = None):
        if self._initialized:
            return

        self._initialized = True
        self._lock = threading.Lock()

        self.storage_dir = Path(storage_dir) if storage_dir else Path.cwd() / ".token_tracking"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.records: List[UsageRecord] = []
        self.session_stats = SessionStats(
            start_time=datetime.now().isoformat()
        )

        logger.info(f"TokenTracker initialized. Storage: {self.storage_dir}")

    def get_pricing(self, model: str) -> Dict[str, float]:
        """Model için fiyatlandırma bilgisi al."""
        # Try exact match
        if model in MODEL_PRICING:
            return MODEL_PRICING[model]

        # Try partial match (for versioned models)
        for key in MODEL_PRICING:
            if key in model or model in key:
                return MODEL_PRICING[key]

        logger.warning(f"Unknown model pricing: {model}. Using default.")
        return DEFAULT_PRICING

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """Maliyet hesapla."""
        pricing = self.get_pricing(model)

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
        }

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        context: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> UsageRecord:
        """
        API çağrısı kullanımını kaydet.

        Args:
            model: Model adı (e.g., "gpt-4o-mini")
            input_tokens: Input token sayısı
            output_tokens: Output token sayısı
            context: İşlem türü (e.g., "entry_generation", "comment")
            agent_name: Agent adı (e.g., "alarm_dusmani")

        Returns:
            UsageRecord: Oluşturulan kayıt
        """
        costs = self.calculate_cost(model, input_tokens, output_tokens)

        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=costs["input_cost"],
            output_cost=costs["output_cost"],
            total_cost=costs["total_cost"],
            context=context,
            agent_name=agent_name,
        )

        with self._lock:
            self.records.append(record)
            self._update_stats(record)

        return record

    def _update_stats(self, record: UsageRecord):
        """İstatistikleri güncelle."""
        stats = self.session_stats

        # Totals
        stats.total_calls += 1
        stats.total_input_tokens += record.input_tokens
        stats.total_output_tokens += record.output_tokens
        stats.total_cost += record.total_cost

        # By model
        if record.model not in stats.by_model:
            stats.by_model[record.model] = {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            }
        stats.by_model[record.model]["calls"] += 1
        stats.by_model[record.model]["input_tokens"] += record.input_tokens
        stats.by_model[record.model]["output_tokens"] += record.output_tokens
        stats.by_model[record.model]["cost"] += record.total_cost

        # By agent
        if record.agent_name:
            if record.agent_name not in stats.by_agent:
                stats.by_agent[record.agent_name] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }
            stats.by_agent[record.agent_name]["calls"] += 1
            stats.by_agent[record.agent_name]["input_tokens"] += record.input_tokens
            stats.by_agent[record.agent_name]["output_tokens"] += record.output_tokens
            stats.by_agent[record.agent_name]["cost"] += record.total_cost

        # By context
        if record.context:
            if record.context not in stats.by_context:
                stats.by_context[record.context] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }
            stats.by_context[record.context]["calls"] += 1
            stats.by_context[record.context]["input_tokens"] += record.input_tokens
            stats.by_context[record.context]["output_tokens"] += record.output_tokens
            stats.by_context[record.context]["cost"] += record.total_cost

    def get_report(self) -> Dict[str, Any]:
        """Detaylı kullanım raporu al."""
        with self._lock:
            stats = self.session_stats
            stats.end_time = datetime.now().isoformat()

            return {
                "session": {
                    "start_time": stats.start_time,
                    "end_time": stats.end_time,
                    "duration_seconds": self._calculate_duration(),
                },
                "totals": {
                    "calls": stats.total_calls,
                    "input_tokens": stats.total_input_tokens,
                    "output_tokens": stats.total_output_tokens,
                    "total_tokens": stats.total_input_tokens + stats.total_output_tokens,
                    "total_cost": round(stats.total_cost, 6),
                    "total_cost_formatted": f"${stats.total_cost:.4f}",
                },
                "by_model": {
                    model: {
                        **data,
                        "cost_formatted": f"${data['cost']:.4f}",
                    }
                    for model, data in stats.by_model.items()
                },
                "by_agent": {
                    agent: {
                        **data,
                        "cost_formatted": f"${data['cost']:.4f}",
                    }
                    for agent, data in stats.by_agent.items()
                },
                "by_context": {
                    ctx: {
                        **data,
                        "cost_formatted": f"${data['cost']:.4f}",
                    }
                    for ctx, data in stats.by_context.items()
                },
            }

    def _calculate_duration(self) -> float:
        """Oturum süresini hesapla."""
        start = datetime.fromisoformat(self.session_stats.start_time)
        end = datetime.now()
        return (end - start).total_seconds()

    def get_summary(self) -> str:
        """Kısa özet string."""
        report = self.get_report()
        t = report["totals"]

        lines = [
            "=" * 50,
            "TOKEN USAGE SUMMARY",
            "=" * 50,
            f"Total API Calls: {t['calls']}",
            f"Input Tokens:    {t['input_tokens']:,}",
            f"Output Tokens:   {t['output_tokens']:,}",
            f"Total Tokens:    {t['total_tokens']:,}",
            "-" * 50,
            f"TOTAL COST:      {t['total_cost_formatted']}",
            "=" * 50,
        ]

        if report["by_model"]:
            lines.append("\nBy Model:")
            for model, data in report["by_model"].items():
                lines.append(f"  {model}: {data['calls']} calls, {data['cost_formatted']}")

        if report["by_agent"]:
            lines.append("\nBy Agent:")
            for agent, data in sorted(report["by_agent"].items(), key=lambda x: -x[1]["cost"]):
                lines.append(f"  {agent}: {data['calls']} calls, {data['cost_formatted']}")

        return "\n".join(lines)

    def save_report(self, filename: Optional[str] = None):
        """Raporu dosyaya kaydet."""
        if filename is None:
            filename = f"token_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.storage_dir / filename

        report = self.get_report()
        report["records"] = [asdict(r) for r in self.records]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Token report saved: {filepath}")
        return filepath

    def reset(self):
        """Tracker'ı sıfırla (test için)."""
        with self._lock:
            self.records.clear()
            self.session_stats = SessionStats(
                start_time=datetime.now().isoformat()
            )


# ============ Singleton Access ============

_tracker_instance: Optional[TokenTracker] = None


def get_tracker(storage_dir: Optional[Path] = None) -> TokenTracker:
    """Global token tracker instance al."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = TokenTracker(storage_dir)
    return _tracker_instance


def reset_tracker():
    """Tracker'ı sıfırla (test için)."""
    global _tracker_instance
    if _tracker_instance is not None:
        _tracker_instance.reset()


def track_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    context: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> UsageRecord:
    """Convenience function to record usage."""
    return get_tracker().record_usage(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        context=context,
        agent_name=agent_name,
    )


# ============ Cost Estimation Helpers ============

def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Dict[str, float]:
    """Maliyet tahmini (kayıt yapmadan)."""
    return get_tracker().calculate_cost(model, input_tokens, output_tokens)


def estimate_simulation_cost(
    num_agents: int,
    ticks_per_agent: int,
    actions_per_tick: float = 0.5,
    avg_input_tokens: int = 300,
    avg_output_tokens: int = 200,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Simülasyon maliyet tahmini.

    Args:
        num_agents: Agent sayısı
        ticks_per_agent: Agent başına tick sayısı
        actions_per_tick: Tick başına ortalama aksiyon (0.0-1.0)
        avg_input_tokens: Ortalama input token
        avg_output_tokens: Ortalama output token
        model: Kullanılacak model

    Returns:
        Maliyet tahmini detayları
    """
    total_actions = int(num_agents * ticks_per_agent * actions_per_tick)
    total_input = total_actions * avg_input_tokens
    total_output = total_actions * avg_output_tokens

    costs = estimate_cost(model, total_input, total_output)
    pricing = get_tracker().get_pricing(model)

    return {
        "model": model,
        "pricing": {
            "input_per_1m": f"${pricing['input']:.2f}",
            "output_per_1m": f"${pricing['output']:.2f}",
        },
        "estimates": {
            "total_actions": total_actions,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
        },
        "cost": {
            "input_cost": f"${costs['input_cost']:.4f}",
            "output_cost": f"${costs['output_cost']:.4f}",
            "total_cost": f"${costs['total_cost']:.4f}",
        },
    }


def format_cost_report(report: Dict[str, Any]) -> str:
    """Maliyet raporunu okunabilir formata çevir."""
    lines = [
        "=" * 60,
        "COST ESTIMATION REPORT",
        "=" * 60,
        f"Model: {report['model']}",
        f"Pricing: Input {report['pricing']['input_per_1m']}/1M, Output {report['pricing']['output_per_1m']}/1M",
        "-" * 60,
        "Estimates:",
        f"  Total Actions:     {report['estimates']['total_actions']:,}",
        f"  Input Tokens:      {report['estimates']['total_input_tokens']:,}",
        f"  Output Tokens:     {report['estimates']['total_output_tokens']:,}",
        f"  Total Tokens:      {report['estimates']['total_tokens']:,}",
        "-" * 60,
        "Cost Breakdown:",
        f"  Input Cost:        {report['cost']['input_cost']}",
        f"  Output Cost:       {report['cost']['output_cost']}",
        f"  TOTAL COST:        {report['cost']['total_cost']}",
        "=" * 60,
    ]
    return "\n".join(lines)
