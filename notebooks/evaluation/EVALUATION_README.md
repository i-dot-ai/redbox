# Redbox RAG Evaluation

We want to be to baseline Redbox RAG performance and from there continually improve it. In order to do this we will use evaluation metrics that have emerged in the AI community, against the Redbox RAG chat endpoint. This will allow us to compare different configurations of our RAG pipeline to see whether these improve Redbox perofmrance or not.

## Overview

The ultimate aim of any RAG evaluation should be an end-to-end (e2e) evaluation of the RAG pipeline. This e2e evaluation will be a combination of retrieval evaluation and generation evaluation. 

RAG pipelines have many 'hyperparameters' that can be optimised.


**An aim for future is to make this experimentation process faster and better tracked**

For now, this notebook links to all the files where `RAG prompts` can be changed to try and optimise Redbox Core API performance


### Evaluation dataset

In order to perform evaluation, we need a suitable dataset.

**Evaluate Redbox RAG chat on one stable, numbered version of these data**

The notebook to generate evaluation dataset can be found [**HERE**](/notebooks/evaluation/evaluation_dataset_generation.ipynb)

### End-to-end evaluation
Notebook for RAG end-to-end evaluation can be found [**HERE**](/notebooks/evaluation/rag_e2e_evaluation.ipynb)





### Tracking evaluation
[2024-05-14] 

We have a basic mlflow setup in the Redbox repo and this seems like a natural place to track RAG evaluation experimentation. This, however, requires a little bit of set up, so focusing on setting up the evaluation notebooks for now



### Workflow for RAG hyperparameter experimentation
1. Review the various locations in the codebase where `RAG prompts` are used
2. Make a change in one or more of these locations
3. Rebuild the core-api docker image (and any other images modified), using `docker compose rebuild --no-cache`
4. Follow the rag_e2e_evaluation notebook to generate evaluation score for the modified Redbox RAG based on your changes
5. Record your changes in **TBD**


### RAG prompt locations
#### 1. Prompts in core.py
One prompt, the `_core_redbox_prompt` is located in [core.py](../../redbox/llm/prompts/core.py)


```python
_core_redbox_prompt = """You are RedBox Copilot. An AI focused on helping UK Civil Servants, Political Advisors and\
Ministers triage and summarise information from a wide variety of sources. You are impartial and\
non-partisan. You are not a replacement for human judgement, but you can help humans\
make more informed decisions. If you are asked a question you cannot answer based on your following instructions, you\
should say so. Be concise and professional in your responses. Respond in markdown format.

=== RULES ===

All responses to Tasks **MUST** be translated into the user's preferred language.\
This is so that the user can understand your responses.\
"""
```

```python
CORE_REDBOX_PROMPT = PromptTemplate.from_template(_core_redbox_prompt)
```
The _core_redbox_prompt is used in combination with _with_sources_templete in the prompt template in the next section

#### 2. Prompts in chat.py
There are 4 prompts located in [chat.py](../../redbox/llm/prompts/chat.py)

Things to experiment with:
1. `_with_sources_template`
2. `WITH_SOURCES_PROMPT`
3. `_stuff_document_template`
4. `STUFF_DOCUMENT_PROMPT`

```python
_with_sources_template = """Given the following extracted parts of a long document and \
a question, create a final answer with Sources at the end.  \
If you don't know the answer, just say that you don't know. Don't try to make \
up an answer.
Be concise in your response and summarise where appropriate. \
At the end of your response add a "Sources:" section with the documents you used. \
DO NOT reference the source documents in your response. Only cite at the end. \
ONLY PUT CITED DOCUMENTS IN THE "Sources:" SECTION AND NO WHERE ELSE IN YOUR RESPONSE. \
IT IS CRUCIAL that citations only happens in the "Sources:" section. \
This format should be <DocX> where X is the document UUID being cited.  \
DO NOT INCLUDE ANY DOCUMENTS IN THE "Sources:" THAT YOU DID NOT USE IN YOUR RESPONSE. \
YOU MUST CITE USING THE <DocX> FORMAT. NO OTHER FORMAT WILL BE ACCEPTED.
Example: "Sources: <DocX> <DocY> <DocZ>"

Use **bold** to highlight the most question relevant parts in your response.
If dealing dealing with lots of data return it in markdown table format.

QUESTION: {question}
=========
{summaries}
=========
FINAL ANSWER:"""
```

```python
WITH_SOURCES_PROMPT = PromptTemplate.from_template(_core_redbox_prompt + _with_sources_template)

_stuff_document_template = "<Doc{parent_doc_uuid}>{page_content}</Doc{parent_doc_uuid}>"

STUFF_DOCUMENT_PROMPT = PromptTemplate.from_template(_stuff_document_template)
```

[Back to top](#title)

#### 3. LLM being used
We can also optimise the LLM being used, but please **bear in mind that prompts are per LLM and if you change the LLM you will need to optimise the prompts!**

For now, please stick with gpt-3.5-turbo, as we establish a baseline quality


## Promote optimised prompts into production
If you find changes to the prompts above improve the generation evaluation scores, please consider making a PR to update the code in `core_api`. Follow these steps:

1. Create a new branch off `main`
2. Make changes in the locations listed below
3. Run through the e2e RAG evaluation notebook
4. If e2e RAG evaluation metrics are improved, please make a PR!

All these prompts are locations in [chat.py](../../redbox/llm/prompts/chat.py), except `_core_redbox_prompt` which is located in [core.py](../../redbox/llm/prompts/core.py)

[Back to top](#title)

--------------------------