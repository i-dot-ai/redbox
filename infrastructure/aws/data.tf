locals {
  record_prefix = terraform.workspace == "prod" ? var.project_name : "${var.project_name}-${terraform.workspace}"
  django_host   = "${local.record_prefix}.${var.domain_name}"
  name          = "${var.team_name}-${terraform.workspace}-${var.project_name}"

  core_api_environment_variables = merge(
    local.worker_environment_variables,
    {
      "OPENAI_API_VERSION" : var.openai_api_version,
      "AZURE_OPENAI_MODEL" : var.azure_openai_model,
      "AI__RAG_K" : var.rag_k,
      "AI__RAG_NUM_CANDIDATES": var.rag_num_candidates,
      "AI__RAG_DESIRED_CHUNK_SIZE": var.rag_desired_chunk_size,
      "AI__RETRIEVAL_SYSTEM_PROMPT": var.retrieval_system_prompt,
      "AI__RETRIEVAL_QUESTION_PROMPT": var.retrieval_question_prompt,
      "AI__SUMMARISATION_SYSTEM_PROMPT": var.summarisation_system_prompt,
      "AI__SUMMARISATION_QUESTION_PROMPT": var.summarisation_question_prompt,
    }
  )

  django_app_environment_variables = {
    "OBJECT_STORE" : "s3",
    "BUCKET_NAME" : aws_s3_bucket.user_data.bucket,
    "POSTGRES_DB" : module.rds.db_instance_name,
    "CORE_API_HOST" : "${aws_service_discovery_service.service_discovery_service.name}.${aws_service_discovery_private_dns_namespace.private_dns_namespace.name}",
    "CORE_API_PORT" : 5002,
    "ENVIRONMENT" : upper(terraform.workspace),
    "DJANGO_SETTINGS_MODULE" : "redbox_app.settings",
    "DEBUG" : terraform.workspace == "dev",
    "AWS_REGION" : var.region,
    "FROM_EMAIL" : var.from_email,
    "GOVUK_NOTIFY_PLAIN_EMAIL_TEMPLATE_ID" : var.govuk_notify_plain_email_template_id,
    "EMAIL_BACKEND_TYPE" : "GOVUKNOTIFY",
    "USE_STREAMING" : true,
    "DJANGO_LOG_LEVEL" : "DEBUG",
    "COMPRESSION_ENABLED" : true,
    "CONTACT_EMAIL" : var.contact_email,
    "FILE_EXPIRY_IN_DAYS" : 30,
    "MAX_SECURITY_CLASSIFICATION" : "OFFICIAL_SENSITIVE",
    "SENTRY_ENVIRONMENT" : var.sentry_environment
  }

  worker_environment_variables = {
    "ELASTIC_ROOT_INDEX" : "redbox-data-${terraform.workspace}",
    "BUCKET_NAME" : aws_s3_bucket.user_data.bucket,
    "OBJECT_STORE" : "s3",
    "EMBEDDING_MODEL" : "all-mpnet-base-v2",
    "EMBED_QUEUE_NAME" : "redbox-embedder-queue",
    "INGEST_QUEUE_NAME" : "redbox-ingester-queue",
    "REDIS_HOST" : module.elasticache.redis_address,
    "REDIS_PORT" : module.elasticache.redis_port,
    "ENVIRONMENT" : upper(terraform.workspace),
    "DEBUG" : terraform.workspace == "dev",
    "AWS_REGION" : var.region,
  }

  core_secrets = {
    "ELASTIC__API_KEY" : var.elastic_api_key,
    "ELASTIC__CLOUD_ID" : var.cloud_id,
    "AZURE_OPENAI_API_KEY" : var.azure_openai_api_key,
    "AZURE_OPENAI_ENDPOINT" : var.azure_openai_endpoint,
    "LLM_MAX_TOKENS" : 1024,
  }

  django_app_secrets = {
    "DJANGO_SECRET_KEY" : var.django_secret_key,
    "POSTGRES_PASSWORD" : module.rds.rds_instance_db_password,
    "POSTGRES_HOST" : module.rds.db_instance_address,
    "POSTGRES_USER" : module.rds.rds_instance_username,
    "GOVUK_NOTIFY_API_KEY" : var.govuk_notify_api_key,
    "SENTRY_DSN" : var.sentry_dsn,
  }

  worker_secrets = {
    "ELASTIC__API_KEY" : var.elastic_api_key,
    "ELASTIC__CLOUD_ID" : var.cloud_id,
  }

  reconstructed_worker_secrets = [ for k, _ in local.worker_secrets : {name = k, valueFrom = "${aws_secretsmanager_secret.worker-secret.arn}:${k}::" }]
  reconstructed_core_secrets = [ for k, _ in local.core_secrets : {name = k, valueFrom = "${aws_secretsmanager_secret.core-api-secret.arn}:${k}::" }]
  reconstructed_django_secrets = [ for k, _ in local.django_app_secrets : {name = k, valueFrom = "${aws_secretsmanager_secret.django-app-secret.arn}:${k}::" }]
}

data "terraform_remote_state" "vpc" {
  backend   = "s3"
  workspace = terraform.workspace
  config = {
    bucket = var.state_bucket
    key    = "vpc/terraform.tfstate"
    region = var.region
  }
}


data "terraform_remote_state" "platform" {
  backend   = "s3"
  workspace = terraform.workspace
  config = {
    bucket = var.state_bucket
    key    = "platform/terraform.tfstate"
    region = var.region
  }
}

data "terraform_remote_state" "universal" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "universal/terraform.tfstate"
    region = var.region
  }
}
