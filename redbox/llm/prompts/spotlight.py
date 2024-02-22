from langchain.prompts.prompt import PromptTemplate

from llm.prompts.core import _core_redbox_prompt

# ==================== SUMMARY ====================

_spotlight_summary_template = """=== TASK INSTRUCTIONS ===
You will be given a document or multiple documents containted in <DocX> tags, X will be a UUID. \
The X indicates the document number. Docs can be of numerous formats and topics. \
Some will be informational, some communications, some policy, some data. \
Respond with a markdown formatted summary of the text. \
Your summary should be no more than 3 sentences for all of the documents combined. \
If dealing with many documents you can use more sentences, but brevity is better. \
Be sure to give a combined summary of all the documents and not just one of them. \
If some of the documents aren't on the same topic, give a summary for each topic. \
RESPOND WITH NO PREAMBLE (e.g. No 'Here is the summary of...').\
Use the provided current date and time to refer to dates in the text in the correct tense. \
If dealing with multiple <DocX> tags, combine the summaries into one. \
If dealing with multiple documents reference them directly in your response as a single tag \
(e.g. "In the email <DocX> from Y..."). \
If dealing with just a single document don't reference it with any tags, just give a summary. \
Do not include any of the above examples in your response. \
IF CITING, CITATIONS MUST BE IN THE FOLLOWING FORMAT: <DocX>. No other brackets are acceptable. \

The summary from this task **MUST BE TRANSLATED** into the user's preferred language (default British English) \
no matter the original language.\
This is so that the user can understand your responses.\

{text} \
"""

SPOTLIGHT_SUMMARY_TASK_PROMPT = PromptTemplate.from_template(
    _core_redbox_prompt + _spotlight_summary_template
)

# ==================== KEY PEOPLE ====================

_key_people_template = """=== TASK INSTRUCTIONS ===
You will be given a document or multiple documents containted in <DocX> tags, X will be a UUID. \
The X indicates the document number. \
Respond with markdown formatted list of key people from the text. \
RESPOND WITH NO PREAMBLE (e.g. NO 'Here are the key people from...' AT ALL).\
Use bold in markdown for people's names followed by a very short \
description of their role/position if available. \
If multiple roles are mentioned for a person, use a comma to separate them include the \
only the most relevant/recent roles. \
Each person should be on a new line as markdown list item. \
If there are groups of people associated with a particular organisation or \
group, list them under a "##### ORG NAME" sub header for all the people from that org. \
Use your knowledge of the user and Civil Service to expand on acronyms, titles, and abbreviations. \
For Documents containing foreign languages and different alphabets please \
romanise the names and then provide the native language version in brackets.\
If dealing with multiple <DocX> tags, combine the people into one big combined list. \
If dealing with multiple documents reference them directly in your response for each item as a single tag \
(e.g. "- **Name** -  Role/title"). \
If dealing with just one document don't reference it with any tags. \

All responses to Tasks **MUST BE TRANSLATED** into the user's preferred language no matter the original language.\
This is so that the user can understand your responses.\

Do not include any of the above examples in your response. \

{text} \
"""

SPOTLIGHT_KEY_PEOPLE_TASK_PROMPT = PromptTemplate.from_template(
    _core_redbox_prompt + _key_people_template
)

# ==================== KEY ACTIONS ====================

_key_actions_template = """=== TASK INSTRUCTIONS ===
You will be given a document or multiple documents containted in <DocX> tags, X will be a UUID. \
The X indicates the document number. Docs can be of numerous formats and topics. \
Some will be informational, some communications, some policy, some data. \
Respond with markdown formatted list of key actions from the text. \
RESPOND WITH NO PREAMBLE (e.g. No 'Here are the key actions from...').\
Your response should have three subheaders for each of the following categories: \
'#### Upcoming' and '#### Ongoing'.\
Each list item should ideally begin with a date in the format YYYY-MM-DD where possible. \
Less specific dates are also acceptable (e.g. 'Next week', 'In the next few months'). \
Those less specific dates should be converted to the format YYYY-MM or YYYY as appropriate. \
Date ranges are also acceptable (e.g. '2022-2023', '2023 09-12'). \
If the action is directly for the User in the document (e.g. an email to user) \
YOU MUST directly address them in your response. \
If the action is for a third party, address the third party in your response. \
Use bold in markdown for people's and organisation names. \
Only respond with specific actions and not general information. \
If you can't find any actions, respond with 'No actions found' for each category. \
If no actions are found for any category, write a small note why (e.g. "This is a news \
article that doesn't have any direct actions...")
If dealing with multiple <DocX> tags, combine the extracted actions into one complete and deduplicated list. \
If dealing with multiple documents reference them directly in your response for each item with a single tag \
(e.g. "Y needs to submit the latest data by the end of the day <DocX>"). \
If dealing with just one document don't reference it with any tags. \
IF CITING, CITATIONS MUST BE IN THE FOLLOWING FORMAT: <DocX>. No other brackets are acceptable. \

All responses to Tasks **MUST BE TRANSLATED** into the user's preferred language no matter the original language.\
This is so that the user can understand your responses.\

Do not include any of the above examples in your response. \

{text} \
"""

SPOTLIGHT_KEY_ACTIONS_TASK_PROMPT = PromptTemplate.from_template(
    _core_redbox_prompt + _key_actions_template
)

# ==================== KEY DATES ====================

_key_dates_prompt = """=== TASK INSTRUCTIONS ===
You will be given a document or multiple documents containted in <DocX> tags, X will be a UUID. \
The X indicates the document number. Docs can be of numerous formats and topics. \
Some will be informational, some communications, some policy, some data. \
Respond with markdown formatted list of key dates from the text. \
Use **bold** in markdown for people's and organisation names. \
RESPOND WITH NO PREAMBLE (e.g. No 'Here are the key dates from...').\
Your response should have three subheaders for each of the following categories: \
'#### Future', '#### Present' and '#### Past'.\
Use the provided current date and time to judge what events fall into which category. \
Each list item should ideally begin with a date in the format YYYY-MM-DD where possible. \
Less specific dates are also acceptable (e.g. 'Next week', 'In the next few months'). \
Those less specific dates should be converted to the format YYYY-MM or YYYY as appropriate. \
Date ranges are also acceptable (e.g. '2022-2023', '2023-08 to 2023-11'). \
Only respond with specific events with dates/timeframes and not general information. \
If you can't find any actions, respond with 'No actions found' for each category. \
If no key dates are found for any time frame category, write a small note why (e.g. "This is a \
that doesn't have any key dates...")\
If dealing with multiple <DocX> tags, combine the extracted dates into one complete and deduplicated list. \
If dealing with multiple documents reference them directly in your response for each item with a individual tags \
(e.g. "**2023-11-01**: Y rebuked X after ... <DocX> <DocY>"). \
If dealing with just a single document don't reference it with any tags, the list of dates. \

All responses to Tasks **MUST BE TRANSLATED** into the user's preferred language no matter the original language.\
This is so that the user can understand your responses.\

Do not include any of the above examples in your response. \

{text} \
"""

SPOTLIGHT_KEY_DATES_TASK_PROMPT = PromptTemplate.from_template(
    _core_redbox_prompt + _key_dates_prompt
)

# ==================== KEY DISCUSSION ====================

_key_discussion_prompt = """=== TASK INSTRUCTIONS ===
You will be given a document or multiple documents containted in <DocX> tags, X will be a UUID. \
The X indicates the document number. Docs can be of numerous formats and topics. \
Some will be informational, some communications, some policy, some data. \
Analyse the different people and organisations across the Document or Documents. \
Use informational documents for context only to improve your use Communications summary. \
Don't talk about actions or technical specifics, but just the main beats of the discussion. \
Respond with a markdown list of key themes, discussion topics and points of contention. \
Use **bold** in markdown for people's and organisation names. \
Do not pass judgement in on the items but objectively layout the positions outlined in the text. \
Where possible, attribute the discussions/points/objections to the people/organisations who raise them. \
If given given context of long form conversation and iteration, summarise the changes of positions over time. \
Use the context of who the user is to address any direct discussions in context to them. \
If the discussion directly directly involves the User above in the documents (e.g. an email to user) \
directly address them in your response. (e.g. "- **Y** agreed with your proposals on **X**). \
Only do that when you have high confidence of a match with the User. \
If dealing with multiple <DocX> tags, combine the discussions into one list. \
If dealing with multiple documents reference them directly in your response as a single tag \
(e.g. "In the email <DocX> from Y..."). \
Respond only in the preffered language of the user so translate where needed. \
Respond wih no preamble (e.g. No 'Here are the key dates from...').\

All responses to Tasks **MUST BE TRANSLATED** into the user's preferred language no matter the original language.\
This is so that the user can understand your responses.\

Do not include any of the above examples in your response. \

{text} \
"""

SPOTLIGHT_KEY_DISCUSSION_TASK_PROMPT = PromptTemplate.from_template(
    _core_redbox_prompt + _key_discussion_prompt
)

# ==================== SPOTLIGHT COMBINATION ====================

_spotlight_combination_prompt = """=== TASK INSTRUCTIONS ===
You will be be given multiple summaries of Documents. \
Combine them into a single summary matching the style that they were given to you. \
Respond with a markdown formatted summary of the text. \
Use **bold** in markdown for people's and organisation names. \
Your summary shoudld be concise and aim to deduplicate any information and points. \
If the formats are in various languages, **YOU MUST TRANSLATE** them into the user's preferred language. \
If a task output is corroborated by multiple summaries, be sure to tag any source documents \
mentioned in the summaries. \
(e.g. "Z spoke at a press conference today... <DocX> <DocY>"). \
X and Y will be UUIDs of the source documents. \
DO NOT cite the summaries/spotlights themselves as sources. \
Only cite the source documents which will always have the <DocX> format. \
DO NOT INCLUDE the example string "<DocX>" TAGS IN YOUR RESPONSE. \

{text} \
"""

SPOTLIGHT_COMBINATION_TASK_PROMPT = PromptTemplate.from_template(
    _core_redbox_prompt + _spotlight_combination_prompt
)
