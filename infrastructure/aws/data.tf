locals {
  record_prefix = terraform.workspace == "prod" ? var.project_name : "${var.project_name}-${terraform.workspace}"
  django_host   = "${local.record_prefix}.${var.domain_name}"
  name          = "${var.team_name}-${terraform.workspace}-${var.project_name}"

  environment_variables = {
    "ELASTIC__API_KEY" : var.elastic_api_key,
    "ELASTIC__CLOUD_ID" : var.cloud_id,
    "ELASTIC_ROOT_INDEX" : "redbox-data-${terraform.workspace}",
    "OBJECT_STORE" : "s3",
    "BUCKET_NAME" : aws_s3_bucket.user_data.bucket,
    "EMBEDDING_MODEL" : "all-mpnet-base-v2",
    "EMBED_QUEUE_NAME" : "redbox-embedder-queue",
    "INGEST_QUEUE_NAME" : "redbox-ingester-queue",
    "REDIS_HOST" : module.elasticache.redis_address,
    "REDIS_PORT" : module.elasticache.redis_port,
    # django stuff
    "DJANGO_SECRET_KEY" : var.django_secret_key,
    "POSTGRES_USER" : module.rds.rds_instance_username,
    "POSTGRES_PASSWORD" : module.rds.rds_instance_db_password,
    "POSTGRES_DB" : module.rds.db_instance_name,
    "POSTGRES_HOST" : module.rds.db_instance_address,
    "CORE_API_HOST" : "${aws_service_discovery_service.service_discovery_service.name}.${aws_service_discovery_private_dns_namespace.private_dns_namespace.name}",
    "CORE_API_PORT" : 5002,
    "ENVIRONMENT" : upper(terraform.workspace),
    "DJANGO_SETTINGS_MODULE" : "redbox_app.settings",
    "DEBUG" : terraform.workspace == "dev",
    "AWS_REGION" : var.region,
    "FROM_EMAIL" : var.from_email,
    "OPENAI_API_VERSION" : var.openai_api_version,
    "AZURE_OPENAI_MODEL" : var.azure_openai_model,
    "AZURE_OPENAI_ENDPOINT" : var.azure_openai_endpoint,
    "AZURE_OPENAI_API_KEY" : var.azure_openai_api_key
    "GOVUK_NOTIFY_PLAIN_EMAIL_TEMPLATE_ID" : var.govuk_notify_plain_email_template_id
    "GOVUK_NOTIFY_API_KEY" : var.govuk_notify_api_key,
    "EMAIL_BACKEND_TYPE" : "GOVUKNOTIFY",
    "USE_STREAMING" : true,
    "DJANGO_LOG_LEVEL" : "DEBUG",
    "COMPRESSION_ENABLED" : true,
    "CONTACT_EMAIL" : var.contact_email,
    "FILE_EXPIRY_IN_DAYS" : 30,
    "MAX_SECURITY_CLASSIFICATION" : "OFFICIAL_SENSITIVE",
    "SENTRY_DSN" : var.sentry_dsn,
    "SENTRY_ENVIRONMENT" : var.sentry_environment
  }
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
