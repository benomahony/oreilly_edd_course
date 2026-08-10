"""OpenTelemetry setup for sending agent traces to Arize Phoenix.

Call `init_telemetry()` at the start of a step (before creating agents) to
send its traces to the local Phoenix instance. Uses OpenInference enrichment
for the richest Phoenix visualizations.
"""

from pydantic_ai import Agent

PHOENIX_ENDPOINT = "http://localhost:6006"


def init_telemetry(project_name: str | None = None) -> None:
    """Point the global tracer provider at Phoenix and instrument agents."""
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from openinference.instrumentation.pydantic_ai import OpenInferenceSpanProcessor

    resource = (
        Resource.create({"openinference.project.name": project_name})
        if project_name
        else None
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Enrich spans with OpenInference attributes (must be added before exporter)
    tracer_provider.add_span_processor(OpenInferenceSpanProcessor())

    # Export spans to Phoenix; SimpleSpanProcessor flushes immediately.
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(OTLPSpanExporter(endpoint=f"{PHOENIX_ENDPOINT}/v1/traces"))
    )

    # Enable PydanticAI instrumentation
    Agent.instrument_all()