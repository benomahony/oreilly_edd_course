Extract action items from the transcript.

The output should be a bulleted list, where each line is formatted as:
"- <Assignee>: <Task>"

The task must be a complete phrase describing the action, providing enough context to be understood on its own. The task must be specific and actionable.
- For generic tasks, add essential details. For example, 'Deploy' should become 'Deploy to production.'
- Keep common abbreviations like 'PR'.

If no action items are identified, output "No action items identified."