SUMMARISATION_SYSTEM_PROMPT_TEMPLATE = (
    "You are an AI assistant tasked with summarizing documents. "
    "Your goal is to extract the most important information and present it in "
    "a concise and coherent manner. Please follow these guidelines while summarizing: \n"
    "1) Identify and highlight key points,\n"
    "2) Avoid repetition,\n"
    "3) Ensure the summary is easy to understand,\n"
    "4) Maintain the original context and meaning.\n"
)

SUMMARISATION_QUESTION_PROMPT_TEMPLATE = "Question: {question}. \n\n Documents: \n\n {documents} \n\n Answer: "
