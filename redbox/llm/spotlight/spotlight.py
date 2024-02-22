from llm.prompts.spotlight import (
    SPOTLIGHT_KEY_ACTIONS_TASK_PROMPT,
    SPOTLIGHT_KEY_DATES_TASK_PROMPT,
    SPOTLIGHT_KEY_DISCUSSION_TASK_PROMPT,
    SPOTLIGHT_KEY_PEOPLE_TASK_PROMPT,
    SPOTLIGHT_SUMMARY_TASK_PROMPT,
)
from models.spotlight import SpotlightTask

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
