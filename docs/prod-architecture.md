# Production Architecture

```mermaid
flowchart TB;

    frontend-app[Frontend App]

    subgraph core-api[Core API]
        subgraph file["/file"]
            file-upload["/file/upload"]
            file-ingest["/file/ingest"]
            file-delete["/file/delete"]
            file-search["/file/search"]
            file-chunks["/file/chunks"]
        end

        subgraph chat["/chat"]
            chat-vanilla["/chat/vanilla"]
            chat-rag["/chat/rag"]
            chat-file["/chat/file"]
        end
    end

    subgraph queue[Queue]
        direction LR
        ingest-queue[Ingest Queue]
        embedding-queue[Embedding Queue]
    end

    subgraph elasticsearch-db[Elasticsearch DB]
        redbox-data-file
        redbox-data-chunk
        redbox-data-chunk-vector
    end


    subgraph processing[Processing]
        ingest-worker[Ingest Worker]

        subgraph embedding
            embedding-worker[Embedding Worker]
            embedding-api[Embedding API]
        end
    end

    object-store[(Object Store)]
    llm[[LLM API]]

    %% File upload flow
    frontend-app -- uploads File --> file-upload
    file-upload -- uploads File --> object-store
    file-uploads -- creates File record --> redbox-data-file
    file-upload -- calls --> file-ingest
    file-ingest -- enqueue FileURI --> ingest-queue
    ingest-queue -- dequeues FileURI --> ingest-worker
    ingest-worker -- creates Chunks --> redbox-data-chunk
    ingest-worker -- enqueues ChunkUUIDs --> embedding-queue
    embedding-queue -- dequeues ChunkUUIDs --> embedding-worker
    embedding-worker -- creates Chunk Vectors --> redbox-data-chunk-vector

    %% Vanill Chat flow
    frontend-app -- sends Chat Message --> chat-vanilla
    chat-vanilla -- calls --> llm

    %% RAG Chat flow
    frontend-app -- sends Chat Message --> chat-rag
    chat-rag -- embeds query --> embedding-api
    chat-rag -- queries chunks with embedding --> redbox-data-chunk-vector
    chat-rag -- calls --> llm

    %% File Chat flow
    frontend-app -- sends Chat Message --> chat-file
    chat-file -- queries whole file --> redbox-data-file
    chat-file -- calls --> llm

    %% File search flow
    frontend-app -- sends Search Query --> file-search
    file-search -- embeds query --> embedding-api
    file-search -- queries chunks with embedding --> redbox-data-chunk-vector

    %% File delete flow
    frontend-app -- sends Delete Query --> file-delete
    file-delete -- deletes File record --> redbox-data-file
    file-delete -- deletes Chunks --> redbox-data-chunk
    file-delete -- deletes Chunk Vectors --> redbox-data-chunk-vector

    %% File chunk flow
    frontend-app -- sends Chunk Query --> file-chunks
    file-chunks -- queries Chunks with parent file --> redbox-data-chunk

```



## Services

| Component | AWS | Azure | Local | Purpose/Function |
|-----------|-----|-------|---------|----|
| Object Store | S3 | Blob Storage | Minio | Storage of files |
| Queue | SQS | Storage Queues | RabbitMQ | Distributing many compute tasks |
| Frontend App | ECS | App Service | Docker | NextJS Chat App |
| Core API | ECS | App Service | Docker | FastAPI AI Interaction and DB Intermediary |
| Ingest API | ECS | App Service | Docker | FastAPI Embedding Handling |
| Embedding API | ECS | App Service | Docker | FastAPI File processing |
| Document Database | DynamoDB | CosmosDB | PostGres | Conversation and Doc storage |
| Vector Database | ??? | Cognitive Search | Weaviate | RAG Database |
| Container Registry | ECR | ACR | Harbor | Storage for app containers |
| Embedding API | Bedrock | Azure OpenAI Service | Huggingface Containers | Embedding for docs into VectorDB |
| LLM API | Bedrock | Azure OpenAI Service | Huggingface Containers | Chat model |
| Authentication | Cognito | Entra | ??? | User auth and management |
