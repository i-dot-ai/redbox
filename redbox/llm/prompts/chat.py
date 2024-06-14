from langchain.prompts.prompt import PromptTemplate

from redbox.llm.prompts.core import _core_redbox_prompt

_chat_template = """Given the following conversation and a follow up question,\
rephrase the follow up question to be a standalone question. \
Include the follow up instructions in the standalone question.

Chat History:
{chat_history}
Follow Up Input: {question}
Standalone question:"""

CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_chat_template)


_with_sources_template = """Given the following extracted parts of a long document and \
a question, create a final answer with Sources at the end.  \
If you don't know the answer, just say that you don't know. Don't try to make \
up an answer.
If a user asks for a particular format to be returned, such as bullet points, then please use that format. \
If a user asks for bullet points you MUST give bullet points. \
If the user asks for a specific number or range of bullet points you MUST give that number of bullet points. \
For example
QUESTION: Please give me 6-8 bullet points on tigers
FINAL ANSWER: - Tigers are orange. \n- Tigers are big. \n- Tigers are scary. \n- Tigers are cool. \n- Tigers are \
cats. -\n Tigers are animals. \

If the number of bullet points a user asks for is not supported by the amount of information that you have, then \
say so, else give what the user asks for. \

At the end of your response do not add a "Sources:" section with the documents you used. \
DO NOT NAME CITED DOCUMENTS IN YOUR RESPONSE. \

Use **bold** to highlight the most question relevant parts in your response.
If dealing dealing with lots of data return it in markdown table format.

QUESTION: {question}
=========
{summaries}
=========
FINAL ANSWER:"""

WITH_SOURCES_PROMPT = PromptTemplate.from_template(_core_redbox_prompt + _with_sources_template)

_stuff_document_template = "<Doc{parent_doc_uuid}>{page_content}</Doc{parent_doc_uuid}>"

STUFF_DOCUMENT_PROMPT = PromptTemplate.from_template(_stuff_document_template)
