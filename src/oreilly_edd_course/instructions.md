Extract concrete, agreed-upon action items from the meeting transcript.

An action item is a specific, measurable task assigned to an individual who has explicitly or implicitly agreed to complete it.

Look for phrases of commitment, which can be direct ("I will...", "I'll take that on", "Consider it done") or simple acknowledgements in response to a request ("Okay", "Sure", "Yep, I can do that").

Pay close attention when a manager or lead assigns a task to a specific person. If the person acknowledges the task (e.g., "Got it", "Okay") or does not object, it is an action item. Also, capture commitments made in response to questions like "Who can take this on?" or "Alex, can you handle that?".

Do NOT extract:
- Vague statements or general suggestions (e.g., "We should look into that", "Someone needs to handle marketing").
- Hypothetical or conditional tasks (e.g., "If we get the budget, we could...").
- Unresolved discussions or questions (e.g., "Maybe we should think about a new design?").
- A task for someone just because they are discussing the topic. A person talking about a task is not the same as being assigned it or committing to it. The assignment must be clear.

- **Meeting Date (`meeting_date`)**: The meeting date is usually mentioned at the beginning of the transcript. Find the explicit date of the meeting.
- **Owners (`who`)**: The owner must be a single person who agreed to the task. If a manager assigns a task, the assignee's lack of objection counts as agreement. Do not assign items to "the team" or multiple people.
- **Action (`what`)**: The description must be a clear, standalone task starting with an action verb (e.g., "Send", "Schedule", "Review"). It must be specific enough that an external person can understand what needs to be done. Avoid vague descriptions like "Follow up with finance".
- **Due Dates (`when`)**: Extract the specific due date if mentioned. If a relative date is given (e.g., "by next Wednesday"), calculate the actual date based on the `meeting_date`.
- **Priority (`criticality`)**: Assign 'high', 'medium', or 'low' based on any explicit statements of urgency. If no priority is mentioned, use your judgment based on the context.
- **Guiding Principle**: Your goal is to balance comprehensiveness with precision. Capture every clear commitment, but avoid creating action items from ambiguous conversations.