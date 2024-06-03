# 📮 Redbox RAG evaluation

How can we unlock analysists of all technical abilities to produce reproducible, sharable, actionable evaluations of Redbox's RAG system?

In this subdirectory, we aim to provide a common workflow so that no matter your department or profession, you can help make Redbox better.

## Overview

The ultimate aim of any RAG evaluation should be an end-to-end (e2e) evaluation of the RAG pipeline. This pipeline covers all combinations and configurations of:

* Chunking
* Embedding
* Retrieval
* Prompts

With such a vast hyperparameter space, the first principle of our evaluation is that:

> [!NOTE]  
> **Data is immutable.** Analysis is done on static, versioned datasets so our insights share a common subject.

We therefore conceptualise evaluation as containing two roles:

* I want to **create a new versioned dataset** for my colleagues to study
* I want to **study a versioned dataset** I've been given to improve Redbox

## 📚 Creating a versioned dataset

> [!NOTE]  
> **Create a versioned datase**t with [`evaluation_dataset_generation.ipynb`](/notebooks/evaluation/rag_e2e_evaluation.ipynb)

The goal of this notebook is to create a filesystem of data ready-made for others to study:

```text
.
└── evaluation/
    └── data/
        └── {version_number}/
            ├── chunks           # the chunked documents of study
            ├── raw              # the raw documents of study
            ├── results          # results from using this data
            ├── synthetic        # Q&A datasets of study created with RAGAS
            └── embeddings/      # vector store dumps of pre-embedded document chunks
                └── {model}
```

We use [RAGAS](https://ragas.io) to create synthetic data, but are more than happy for users to manually create datasets too.

## 🔎 Studying a versioned dataset

> [!NOTE]  
> **Study** a versioned dataset with [`rag_e2e_evaluation.ipynb`](/notebooks/evaluation/rag_e2e_evaluation.ipynb)

The goal of this notebook is that everything you need to study a versioned dataset should be contained in a single place that evaluators can run end to end.

We use [DeepEval](https://docs.confident-ai.com) to evaluate datasets.

Right now the notebook only contains the final retrieval engine: the interplay of prompts and retriever. Chunking and embedding strategies will need to be loaded outside this notebook, though you can certainly assess them using it.

## ✅ Success! What now?

You've analysed a dataset, improved the RAG system, and you want those changes to make it into Redbox. Congratulations! 

If you feel confident enough to raise the PR yourself, you should, but we believe that great evaluation can come from a plurality of backgrounds.

> [!NOTE]  
> **Evaluation doesn't need to be done by engineers.** Raise an issue with your evidence, and we'll implement it.

If you can evidence that your notebook performs better than production, we can take it from there.

## ❌ Failure! What now?

Either as an evaluator or user, you've found a significant problem with the RAG system. Perhaps you're even struggling to explain exactly what's wrong, merely that it's "worse". Here we attempt to provide some clear actions to help refine responses to problems like this.

We believe there's two ways we might fix this in our evaluation loop:

### We need more data!

Perhaps you've seen a document used in Redbox that performs badly, or a certain order of questions produces strange results.

In this case we need to **create a new versioned dataset**. This might contain more source documents that better-cover the problem space, or more nuanced or difficult Q&A scenarios to better-describe user interactions. Either way, we need more data.

### We need better metrics!

Perhaps a user has given a piece of feedback that maps poorly onto our existing metrics. In early versions, for example, some users felt replies were too short.

There are more metrics available for RAG systems than the ones we use, and it's potentially time to add another, or even develop our own. In this case we want to **extend our study of a versioned dataset** to add more appropriate measures of the things users care about.
