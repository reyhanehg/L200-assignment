"""OpenTelemetry Tracing and Observability Metrics."""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional

from src.config import settings
from src.observability.logging_config import logger

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.app_name, "service.version": settings.app_version})
    )
    if settings.debug:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("nutri_concierge", settings.app_version)
    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False
    tracer = None


class MetricsCollector:
    """Collects runtime operational telemetry and evaluation metrics."""

    def __init__(self):
        self.tool_invocations: Dict[str, int] = {}
        self.agent_latencies_ms: Dict[str, List[float]] = {}
        self.safety_checks_total: int = 0
        self.safety_checks_passed: int = 0
        self.safety_checks_failed: int = 0
        self.total_tokens_estimated: int = 0

    def record_tool_call(self, tool_name: str, duration_ms: float) -> None:
        """Track tool call frequency and latency."""
        self.tool_invocations[tool_name] = self.tool_invocations.get(tool_name, 0) + 1
        if tool_name not in self.agent_latencies_ms:
            self.agent_latencies_ms[tool_name] = []
        self.agent_latencies_ms[tool_name].append(duration_ms)

    def record_safety_check(self, is_safe: bool) -> None:
        """Track allergen & dietary safety check pass/fail rate."""
        self.safety_checks_total += 1
        if is_safe:
            self.safety_checks_passed += 1
        else:
            self.safety_checks_failed += 1

    def record_tokens(self, count: int) -> None:
        """Estimate token usage."""
        self.total_tokens_estimated += count

    def get_summary(self) -> Dict[str, Any]:
        """Return aggregated observability metrics."""
        pass_rate = (
            (self.safety_checks_passed / self.safety_checks_total * 100.0)
            if self.safety_checks_total > 0
            else 100.0
        )
        return {
            "tool_invocations": self.tool_invocations,
            "safety_checks": {
                "total": self.safety_checks_total,
                "passed": self.safety_checks_passed,
                "failed": self.safety_checks_failed,
                "pass_rate_pct": round(pass_rate, 2),
            },
            "total_tokens_estimated": self.total_tokens_estimated,
        }


metrics = MetricsCollector()


class MockSpan:
    """Mock span for environments without opentelemetry sdk installed."""
    def __init__(self, name: str):
        self.name = name
        self.attributes: Dict[str, str] = {}

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = str(value)


@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager for tracing execution blocks with OpenTelemetry."""
    start_time = time.perf_counter()
    if HAS_OPENTELEMETRY and tracer:
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))
            try:
                yield span
            finally:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                span.set_attribute("duration_ms", elapsed_ms)
    else:
        span = MockSpan(name)
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
        try:
            yield span
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            span.set_attribute("duration_ms", elapsed_ms)


def trace_agent_execution(agent_name: str):
    """Decorator to trace agent reasoning steps."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            with trace_span(f"agent.{agent_name}.execute", {"agent": agent_name}):
                try:
                    result = func(*args, **kwargs)
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    metrics.record_tool_call(agent_name, elapsed_ms)
                    logger.info(
                        f"Agent [{agent_name}] completed execution in {elapsed_ms:.2f}ms",
                        extra={"agent_name": agent_name, "duration_ms": elapsed_ms},
                    )
                    return result
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    logger.error(
                        f"Agent [{agent_name}] execution error: {str(e)}",
                        extra={"agent_name": agent_name, "duration_ms": elapsed_ms},
                        exc_info=True,
                    )
                    raise
        return wrapper
    return decorator


def trace_tool_call(tool_name: str):
    """Decorator to trace tool executions."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            with trace_span(f"tool.{tool_name}.invoke", {"tool": tool_name}):
                try:
                    result = func(*args, **kwargs)
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    metrics.record_tool_call(tool_name, elapsed_ms)
                    logger.debug(
                        f"Tool [{tool_name}] executed in {elapsed_ms:.2f}ms",
                        extra={"tool_name": tool_name, "duration_ms": elapsed_ms},
                    )
                    return result
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    logger.error(
                        f"Tool [{tool_name}] execution failed: {str(e)}",
                        extra={"tool_name": tool_name, "duration_ms": elapsed_ms},
                        exc_info=True,
                    )
                    raise
        return wrapper
    return decorator
