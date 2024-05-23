from collections import defaultdict
from datetime import UTC, datetime
from typing import Optional

from langchain.schema import HumanMessage, SystemMessage

from redbox.llm.prompts.spotlight import SPOTLIGHT_COMBINATION_TASK_PROMPT


class SpotlightCollection(object):
    """A class for combining Spotlight task outputs into a cohesive briefing.

    Args:
        object (_type_): _description_
    """

    def __init__(self, spotlights: list[dict]) -> None:
        self.spotlights = spotlights
        self.combined_spotlight_tasks = defaultdict(list)

        for individual_spotlight_dict in self.spotlights:
            for task_id in individual_spotlight_dict["task_outputs"]:
                self.combined_spotlight_tasks[task_id].append(individual_spotlight_dict["task_outputs"][task_id])
        self.combined_spotlight_dict: dict = {"combined_task_outputs": {}}

    def combine_spotlight_task_outputs(
        self,
        task_outputs: list[dict],
        task_id,
        user_info,
        llm,
        callbacks: Optional[list] = None,
    ):
        """Combine the outputs of a task across all spotlights."""
        spotlight_payload = ""

        for i, individual_task_payload in enumerate(task_outputs):
            spotlight_payload += (
                f"Spotlight {i}: {individual_task_payload['title']}:\n{individual_task_payload['content']}\n\n\n"
            )

        messages_to_send = [
            SystemMessage(
                content=SPOTLIGHT_COMBINATION_TASK_PROMPT.format(
                    current_date=datetime.now(tz=UTC).date().isoformat(),
                    user_info=user_info,
                )
            ),
            HumanMessage(content=spotlight_payload),
        ]

        result = llm(messages_to_send, callbacks=callbacks or [])
        self.combined_spotlight_dict[task_id] = result
        return result
