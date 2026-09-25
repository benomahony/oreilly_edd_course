"""
Custom lexguard lexicons for meeting todos.

Built exactly like lexguard's shipped ones: words that indicate the concept,
words that rule it back out, and a one-sentence fix that becomes the retry
message when the lexicon is used as a guardrail. Kept in their own module so
capabilities authored at runtime can `from oreilly_edd_course.lexicons import ...`.
"""

from lexguard import Actionable, Lexicon

# Extends a shipped lexicon: lexguard's Actionable misses meeting verbs like
# "ping", "schedule" and "audit". `uv run lexguard actionable` prints its source.
TodoVerb = Lexicon(
    name="todo_verb",
    indicates=[
        *Actionable.indicates,
        "audit", "confirm", "create", "document", "get", "line up", "ping", "request",
        "research", "review", "schedule", "send", "set up", "share", "sync", "talk",
    ],
    rules_out=Actionable.rules_out,
    # Something we want to see: a todo with no action verb is the failure.
    fail_when_neutral=True,
    fix="start the todo with the concrete action to take (send, review, schedule...)",
)

# A todo owned by a team or a pronoun is a todo nobody owns.
VagueOwner = Lexicon(
    name="vague_owner",
    indicates=[
        "all", "anyone", "everybody", "everyone", "somebody", "someone", "tbd", "they",
        "unassigned", "us", "we",
        "team", "design", "devops", "engineering", "finance", "marketing", "product", "security",
    ],
    fix="assign the todo to the named attendee who committed to it, not a team or pronoun",
)

# A todo that's really a status report: "X is going well", "Y is on track".
StatusUpdate = Lexicon(
    name="status_update",
    indicates=[
        "going well", "in progress", "is working on", "made progress", "on track", "progress on",
        "status", "update on", "wip",
    ],
    # "Send a status update to Sarah" is a real todo.
    rules_out=["send", "share", "post", "write"],
    fix="drop status reports; keep only actions someone committed to doing",
)
