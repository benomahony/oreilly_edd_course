from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.exceptions import ModelRetry
from lexguard import Hypothetical


class NoHypotheticalTodos(AbstractCapability):
    async def after_output_validate(self, ctx, *, output_context, output):
        for todo in output.todos:
            verdict = Hypothetical.verdict(todo.what)
            if not verdict.passed:
                raise ModelRetry(
                    f"Todo '{todo.what}' seems hypothetical. {verdict.reason}. Stick to concrete commitments."
                )
        return output
