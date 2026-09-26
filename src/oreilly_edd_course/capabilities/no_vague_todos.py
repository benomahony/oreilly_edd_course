from lexguard import Vague
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.exceptions import ModelRetry


class NoVagueTodos(AbstractCapability):
    async def after_output_validate(self, ctx, *, output_context, output):
        for todo in output.todos:
            verdict = Vague.verdict(todo.what)
            if not verdict.passed:
                raise ModelRetry(f"Todo '{todo.what}': {verdict.reason}")
        return output
