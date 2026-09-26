from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.exceptions import ModelRetry


class ConciseTodos(AbstractCapability):
    async def after_output_validate(self, ctx, *, output_context, output):
        for todo in output.todos:
            word_count = len(todo.what.split())
            if word_count > 12:
                raise ModelRetry(
                    f"Todo '{todo.what}' is too long at {word_count} words. It must be 12 words or less."
                )
        return output
