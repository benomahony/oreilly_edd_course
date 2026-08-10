"""
Local AI-native observability demo.

Configures OpenTelemetry to export spans to the local Arize Phoenix stack
(`make obs-up`), then runs an instrumented agent inference so you can
inspect the full trace (prompt, completion, token usage) in the Phoenix UI.

Follows the OpenInference enrichment pattern from the ai-agent-katas repo
for the richest Phoenix visualizations (conversation threading, session
attribution, span metadata).

Usage:
    make obs-up     # start Phoenix
    make obs-run    # run this script
    make obs-ui     # open the Phoenix UI
"""

import asyncio

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

PHOENIX_ENDPOINT = "http://localhost:6006"
PHOENIX_UI = "http://localhost:6006"

model = OpenAIChatModel(
    "meta/muse-glimmer",
    provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm-studio"),
)


class Todo(BaseModel):
    who: str
    what: str


def init_telemetry(project_name: str | None = None) -> None:
    """Initialize OpenTelemetry tracing for Phoenix.

    Args:
        project_name: Project name shown in the Phoenix UI.
    """
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

    # Export spans to Phoenix; SimpleSpanProcessor flushes immediately so the
    # trace is visible in the UI as soon as the script finishes.
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(OTLPSpanExporter(endpoint=f"{PHOENIX_ENDPOINT}/v1/traces"))
    )

    # Enable PydanticAI instrumentation
    Agent.instrument_all()


async def main() -> None:
    # Initialize telemetry BEFORE creating agents
    init_telemetry(project_name="edd-workshop")

    agent = Agent(
        model=model,
        output_type=list[Todo],
        instructions="Extract todos from the transcript as structured data.",
    )
    result = await agent.run(
        "Alice will finalise the budget by Friday. Bob owns the Q3 roadmap."
    )

    print(result.output)
    print(f"\nView the trace in Phoenix: {PHOENIX_UI}")


if __name__ == "__main__":
    asyncio.run(main())