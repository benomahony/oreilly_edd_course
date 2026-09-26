from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.exceptions import ModelRetry
from oreilly_edd_course.lexicons import TodoVerb


class EnforceTodoVerb(AbstractCapability):
    async def after_output_validate(self, ctx, *, output_context, output):
        for todo in output.todos:
            verdict = TodoVerb.verdict(todo.what)
            if not verdict.passed:
                raise ModelRetry(
                    f"Todo '{todo.what}' does not start with a clear action verb. {verdict.reason}."
                )
        return output
