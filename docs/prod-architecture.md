# Production Architecture

| Component | AWS | Azure | Local | Purpose/Function |
|-----------|-----|-------|---------|----|
| Object Store | S3 | Blob Storage | Minio | Storage of files |
| Queue | SQS | Storage Queues | RabbitMQ | Distributing many compute tasks |
| Frontend App | ECS | App Service | Docker | NextJS Chat App |
| AI App | ECS | App Service | Docker | FastAPI AI Interaction and DB Intermediary |
| Ingest App | ECS | App Service | Docker | FastAPI Embedding Handling |
| Embedding App | ECS | App Service | Docker | FastAPI File processing |
| Document Database | DynamoDB | CosmosDB | PostGres | Conversation and Doc storage |
| Vector Database | ??? | Cognitive Search | Weaviate | RAG Database |
| Container Registry | ECR | ACR | Harbor | Storage for app containers |
| Embedding API | Bedrock | Azure OpenAI Service | Huggingface Containers | Embedding for docs into VectorDB |
| LLM API | Bedrock | Azure OpenAI Service | Huggingface Containers | Chat model |
| Authentication | Cognito | Entra | ??? | User auth and management |


