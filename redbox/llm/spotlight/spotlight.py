from redbox.llm.prompts.spotlight import (
    SPOTLIGHT_KEY_ACTIONS_TASK_PROMPT,
    SPOTLIGHT_KEY_DATES_TASK_PROMPT,
    SPOTLIGHT_KEY_DISCUSSION_TASK_PROMPT,
    SPOTLIGHT_KEY_PEOPLE_TASK_PROMPT,
    SPOTLIGHT_SUMMARY_TASK_PROMPT,
)
from redbox.models.spotlight import SpotlightFormat, SpotlightTask

# region ===== TASKS =====

summary_task = SpotlightTask(
    id="summary",
    title="Summary",
    prompt_template=SPOTLIGHT_SUMMARY_TASK_PROMPT,
)
key_dates_task = SpotlightTask(
    id="key_dates",
    title="Key Dates",
    prompt_template=SPOTLIGHT_KEY_DATES_TASK_PROMPT,
)
key_actions_task = SpotlightTask(
    id="key_actions",
    title="Key Actions",
    prompt_template=SPOTLIGHT_KEY_ACTIONS_TASK_PROMPT,
)
key_people_task = SpotlightTask(
    id="key_people",
    title="Key People",
    prompt_template=SPOTLIGHT_KEY_PEOPLE_TASK_PROMPT,
)
key_discussion_task = SpotlightTask(
    id="key_discussion",
    title="Key Discussion",
    prompt_template=SPOTLIGHT_KEY_DISCUSSION_TASK_PROMPT,
)
# endregion

# region ===== TASKS BY FORMAT =====
email_format = SpotlightFormat(
    id="email_letter_or_correspondance",
    tasks=[
        key_discussion_task,
        key_actions_task,
        key_people_task,
    ],
)
meeting_format = SpotlightFormat(
    id="meetings_and_minutes",
    tasks=[
        key_discussion_task,
        key_actions_task,
        key_people_task,
    ],
)
briefing_format = SpotlightFormat(
    id="briefing",
    tasks=[summary_task, key_dates_task],
)
proposal_format = SpotlightFormat(
    id="proposals_and_submissions",
    tasks=[
        summary_task,
        key_discussion_task,
        key_actions_task,
    ],
)
other_format = SpotlightFormat(
    id="other_including_documents",
    tasks=[
        summary_task,
        key_discussion_task,
        key_actions_task,
        key_dates_task,
        key_people_task,
    ],
)
# endregion
