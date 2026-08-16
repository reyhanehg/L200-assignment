"""OpenTelemetry Distributed Tracing, Pre-Execution Intent Logging, and Telemetry Metrics."""

import functools
import os
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from src.observability.logging_config import logger
from src.observability.pii_scrubber import PIIScrubber

# Attempt to import OpenTelemetry SDK components
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    resource = Resource.create({"service.name": "nutri-concierge-ai"})
    provider = TracerProvider(resource=resource)
    if os.getenv("OTEL_CONSOLE_EXPORTER", "false").lower() == "true":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("nutri_concierge")
    HAS_OPENTELEMETRY = True
except Exception:
    HAS_OPENTELEMETRY = False
    tracer = None


class MetricsCollector:
    """Collects runtime execution metrics and safety pass rates."""

    def __init__(self):
        self.tool_invocations: Dict[str, int] = {}
        self.tool_latencies: Dict[str, list] = {}
        self.safety_checks_total: int = 0
        self.safety_checks_passed: int = 0
        self.safety_checks_failed: int = 0
        self.total_tokens_estimated: int = 0

    def record_tool_call(self, tool_name: str, duration_ms: float):
        """Record tool call invocation and execution latency."""
        self.tool_invocations[tool_name] = self.tool_invocations.get(tool_name, 0) + 1
        if tool_name not in self.tool_latencies:
            self.tool_latencies[tool_name] = []
        self.tool_latencies[tool_name].append(duration_ms)

    def record_safety_check(self, passed: bool):
        """Record result of an allergen or dietary reflection safety check."""
        self.safety_checks_total += 1
        if passed:
            self.safety_checks_passed += 1
        else:
            self.safety_checks_failed += 1

    def record_token_usage(self, estimated_tokens: int):
        """Track estimated LLM token usage."""
        self.total_tokens_estimated += estimated_tokens

    def get_summary(self) -> Dict[str, Any]:
        """Generate metrics summary."""
        avg_latencies = {
            tool: sum(lats) / len(lats) for tool, lats in self.tool_latencies.items() if lats
        }
        pass_rate = (
            (self.safety_checks_passed / self.safety_checks_total * 100.0)
            if self.safety_checks_total > 0
            else 100.0
        )
        return {
            "tool_invocations": self.tool_invocations,
            "average_tool_latencies_ms": avg_latencies,
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
    """Mock span for environments without active OpenTelemetry collectors."""

    def __init__(self, name: str):
        self.name = name
        self.attributes = {}

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = PIIScrubber.scrub_data(value)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager for tracing execution blocks with OpenTelemetry and PII scrubbing."""
    start_time = time.perf_counter()
    scrubbed_attributes = PIIScrubber.scrub_data(attributes or {})

    if HAS_OPENTELEMETRY and tracer:
        with tracer.start_as_current_span(name) as span:
            for k, v in scrubbed_attributes.items():
                span.set_attribute(k, str(v))
            try:
                yield span
            finally:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                span.set_attribute("duration_ms", elapsed_ms)
    else:
        span = MockSpan(name)
        for k, v in scrubbed_attributes.items():
            span.set_attribute(k, str(v))
        try:
            yield span
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            span.set_attribute("duration_ms", elapsed_ms)


def trace_agent_execution(agent_name: str):
    """Decorator to trace agent reasoning steps with pre-execution intent logging."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Pre-Execution Intent Logging
            logger.info(
                f"ACTION_INTENDED: Agent [{agent_name}] preparing to execute",
                extra={
                    "agent_name": agent_name,
                    "status": "PENDING_EXECUTION",
                    "action_intended": True,
                },
            )
            start = time.perf_counter()
            with trace_span(f"agent.{agent_name}.execute", {"agent": agent_name}):
                try:
                    result = func(*args, **kwargs)
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    metrics.record_tool_call(agent_name, elapsed_ms)
                    logger.info(
                        f"ACTION_COMPLETED: Agent [{agent_name}] completed execution in {elapsed_ms:.2f}ms",
                        extra={
                            "agent_name": agent_name,
                            "duration_ms": elapsed_ms,
                            "status": "COMPLETED",
                        },
                    )
                    return result
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    logger.error(
                        f"ACTION_FAILED: Agent [{agent_name}] execution error: {str(e)}",
                        extra={
                            "agent_name": agent_name,
                            "duration_ms": elapsed_ms,
                            "status": "FAILED",
                        },
                        exc_info=True,
                    )
                    raise e
        return wrapper
    return decorator


def trace_tool_execution(tool_name: str):
    """Decorator to trace tool execution with pre-execution intent logging and PII scrubbing."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Pre-Execution Intent Logging
            logger.info(
                f"ACTION_INTENDED: Invoking tool [{tool_name}]",
                extra={
                    "tool_name": tool_name,
                    "status": "PENDING_EXECUTION",
                    "action_intended": True,
                },
            )
            start = time.perf_counter()
            with trace_span(f"tool.{tool_name}.execute", {"tool": tool_name}):
                try:
                    result = func(*args, **kwargs)
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    metrics.record_tool_call(tool_name, elapsed_ms)
                    logger.info(
                        f"ACTION_COMPLETED: Tool [{tool_name}] finished in {elapsed_ms:.2f}ms",
                        extra={
                            "tool_name": tool_name,
                            "duration_ms": elapsed_ms,
                            "status": "COMPLETED",
                        },
                    )
                    return result
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000.0
                    logger.error(
                        f"ACTION_FAILED: Tool [{tool_name}] error: {str(e)}",
                        extra={
                            "tool_name": tool_name,
                            "duration_ms": elapsed_ms,
                            "status": "FAILED",
                        },
                        exc_info=True,
                    )
                    raise e
        return wrapper
    return decorator


trace_tool_call = trace_tool_execution
