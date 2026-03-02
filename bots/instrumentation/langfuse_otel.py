"""Langfuse + OpenInference setup helpers."""

import base64
import os

from langfuse import get_client


def configure_langfuse_otel(service_name: str) -> bool:
    """Configure OpenTelemetry exporter for Langfuse if env vars are present."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")
    if not (public_key and secret_key and host):
        return False

    host = host.rstrip("/")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", f"{host}/api/public/otel")
    if "OTEL_EXPORTER_OTLP_HEADERS" not in os.environ:
        auth = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("utf-8")
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth}"
    os.environ.setdefault("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    os.environ.setdefault("OTEL_SERVICE_NAME", service_name)
    return True


def init_openinference() -> None:
    """Initialize OpenInference + OTEL exporter for CrewAI spans."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from openinference.instrumentation.crewai import CrewAIInstrumentor
    except Exception as exc:  # pragma: no cover - best-effort instrumentation
        print(f"OpenInference init skipped: {exc}")
        return

    provider = trace.get_tracer_provider()
    if provider.__class__.__name__ == "ProxyTracerProvider":
        provider = TracerProvider()
        trace.set_tracer_provider(provider)

    if hasattr(provider, "add_span_processor"):
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    CrewAIInstrumentor().instrument()

    # Best-effort LLM instrumentation for token usage.
    try:
        from openinference.instrumentation.litellm import LiteLLMInstrumentor

        LiteLLMInstrumentor().instrument()
    except Exception:
        pass
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor

        OpenAIInstrumentor().instrument()
    except Exception:
        pass


def init_langfuse_tracing(service_name: str):
    """Enable CrewAI tracing to Langfuse when Langfuse env vars are configured."""
    if configure_langfuse_otel(service_name):
        init_openinference()

    langfuse = get_client()

    # Verify connection
    if langfuse.auth_check():
        print("Langfuse client is authenticated and ready!")
    else:
        print("Authentication failed. Please check your credentials and host.")
    return langfuse

