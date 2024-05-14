# Redbox RAG Evaluation

We need to be able to compare different configurations of our RAG pipeline to see whether we are making improvements (either to earlier configuration versions, or to generic non-Redbox approaches).

## Overview

The ultimate aim of any RAG evaluation should be an end-to-end (e2e) evaluation of the RAG pipeline. This e2e evaluation will be a combination of retrieval evaluation and generation evaluation. 

RAG pipelines have many 'hyperparameters' that can be optimised. **To facilitate fast experimentation**, we want to breaking down evaluation into component parts as much as possible. These smaller components can then be fed into (slower) e2e evaluations.


### Generate evaluation dataset

In order to perform evaluation, we need a suitable dataset.

Notebook to generate evaluation dataset can be found [**HERE**](/notebooks/evaluation/evaluation_dataset_generation.ipynb)


### Retrieval evaluation


### Generation evaluation
This could be the easiest part of the RAG pipeline to experiment with, when considering it as an isolated component.
- Mock the retrieved context (i.e. Matched Chunks), for a defined set of questions
- The data scientist would only be experimenting with the `RAG prompts`

N.B. Some RAG prompts may work well with 'perfect context,' but worse when there is lower retrieval quality, so we should give various levels of retrieval quality (precision, recall) of the Matched Chunks

Notebook for generation evaluation can be found [**HERE**](/notebooks/evaluation/rag_generation_evalutation.ipynb)

### End-to-end evaluation





### Tracking evaluation
[2024-05-14] 

We have a basic mlflow setup in the Redbox repo and this seems like a natural place to track RAG evaluation experimentation. This, however, requires a little bit of set up, so focusing on setting up the evaluation notebooks for now










<!-- 


-->

## OLD work

#### REDBOX-204: [SPIKE] Evaluate DeepEval as the LLM evaluation framework for Redbox

Some information about the core components of the DeepEval framework are in `llm_evaluation.ipynb` (more could be added)

However, the made focus on this spike is on RAG, so the `rag_evaluation_basics.ipynb` introduces the topic and how the DeepEval framework can be used to evaluation a RAG pipeline.

`redbox_rag_evaluation.ipynb` is a first pass at applying DeepEval to evaluate the RAG functionality of Redbox.