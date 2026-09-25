"""Send agent traces and online eval results to your Logfire project.

Call `init_telemetry()` once at startup, before running agents. `edd setup` creates
the project and saves its write token to `.logfire/` (gitignored). Without a token,
telemetry stays local and the example still runs.
"""

import logfire


def _keep_evaluator_names(match: logfire.ScrubMatch) -> object:
    # Lexguard's "UnsourcedAuthority" trips the default "auth" secret pattern; it's a name, not a secret.
    if match.pattern_match.group(0).lower() == "auth" and "UnsourcedAuthority" in str(match.value):
        return match.value
    return None


def init_telemetry(service_name: str) -> None:
    logfire.configure(
        service_name=service_name,
        send_to_logfire="if-token-present",
        scrubbing=logfire.ScrubbingOptions(callback=_keep_evaluator_names),
    )
    logfire.instrument_pydantic_ai()
