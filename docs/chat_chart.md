# Chat chain diagram

```mermaid
flowchart LR;
    subgraph input
        chat_history
        question
        vectorstore[(vectorstore)]
    end

    subgraph prompts
        _core_redbox_prompt
        _chat_template
        _with_sources_template
        _stuff_document_template
    end

    subgraph ConversationalRetrievalChain
        _core_redbox_prompt --> chat_history
        _chat_template --> conversation
        conversation{"""question_generator_chain
        (LLM)"""}

        question --> conversation
        chat_history --> conversation
        subgraph question generator
        conversation --> standalone_question
    end

    _with_sources_template --> with_sources
    _stuff_document_template --> metadata
    vectorstore <--> retriever{retriever}
    retriever --> relevant_docs

    subgraph QA Chain with sources
        with_sources{"""combine_docs_chain
        (LLM)"""}
        metadata --> with_sources
    end

    relevant_docs --> metadata{inject metadata}
    standalone_question --> retriever
    standalone_question --> with_sources



 end
with_sources ==> answer
```

 #
 Based on langchain class: `ConversationalRetrievalChain(BaseConversationalRetrievalChain)`:

"This chain takes in chat history (a list of messages) and new questions, and then returns an answer to that question.    The algorithm for this chain consists of three parts:

1. Use the chat history and the new question to create a "standalone question". This is done so that this question can be passed into the retrieval step to fetch   relevant documents. If only the new question was passed in, then relevant context      may be lacking. If the whole conversation was passed into retrieval, there may    be unnecessary information there that would distract from retrieval.

2. This new question is passed to the retriever and relevant documents are  returned.

3. The retrieved documents are passed to an LLM along with either the new question    (default behavior) or the original question and chat history to generate a final    response."
