locals {
  record_prefix     = terraform.workspace == "prod" ? var.project_name : "${var.project_name}-${terraform.workspace}"
  django_host       = "${local.record_prefix}.${var.domain_name}"
  name              = "${var.team_name}-${terraform.workspace}-${var.project_name}"
  ssr_url           = "${aws_service_discovery_service.lit_ssr_service_discovery_service.name}.${aws_service_discovery_private_dns_namespace.private_dns_namespace.name}"
  litellm_url       = "${aws_service_discovery_service.litellm_service_discovery_service.name}.${aws_service_discovery_private_dns_namespace.private_dns_namespace.name}"


  django_app_environment_variables = {
    "ALLOW_SIGN_UPS": var.allow_sign_ups,
    "AZURE_OPENAI_MODEL" : var.azure_openai_model,

    "LIT_SSR_URL": local.ssr_url,

    "OBJECT_STORE" : "s3",
    "BUCKET_NAME" : aws_s3_bucket.user_data.bucket,
    "POSTGRES_DB" : module.rds.db_instance_name,
    "ENVIRONMENT" : upper(terraform.workspace),
    "DJANGO_SETTINGS_MODULE" : "redbox_app.settings",
    "DEBUG" : terraform.workspace == "dev",
    "FROM_EMAIL" : var.from_email,
    "GOVUK_NOTIFY_PLAIN_EMAIL_TEMPLATE_ID" : var.govuk_notify_plain_email_template_id,
    "EMAIL_BACKEND_TYPE" : "GOVUKNOTIFY",
    "DJANGO_LOG_LEVEL" : "INFO",
    "CONTACT_EMAIL" : var.contact_email,
    "FILE_EXPIRY_IN_DAYS" : 30,
    "MAX_SECURITY_CLASSIFICATION" : "OFFICIAL_SENSITIVE",
    "SENTRY_ENVIRONMENT" : var.sentry_environment,
    "SENTRY_REPORT_TO_ENDPOINT" : var.sentry_report_to_endpoint,

    "ELASTIC_ROOT_INDEX" : "redbox-data-${terraform.workspace}",
    "ELASTIC_CHUNK_ALIAS" : "redbox-data-${terraform.workspace}-chunk-current",
    "BUCKET_NAME" : aws_s3_bucket.user_data.bucket,
    "OBJECT_STORE" : "s3",
    "ENVIRONMENT" : upper(terraform.workspace),
    "DEBUG" : terraform.workspace == "dev",
  }

  django_app_secrets = {
    "ELASTIC__API_KEY" : var.elastic_api_key,
    "ELASTIC__CLOUD_ID" : var.cloud_id,

    "AZURE_OPENAI_API_KEY": var.azure_openai_api_key,
    "AZURE_OPENAI_ENDPOINT" : var.azure_openai_endpoint,
    "OPENAI_API_VERSION": var.openai_api_version,

    "LITELLM_URL": local.litellm_url,
    "LITELLM_MASTER_KEY": var.litellm_master_key,


    "DJANGO_SECRET_KEY" : var.django_secret_key,
    "POSTGRES_PASSWORD" : module.rds.rds_instance_db_password,
    "POSTGRES_HOST" : module.rds.db_instance_address,
    "POSTGRES_USER" : module.rds.rds_instance_username,
    "GOVUK_NOTIFY_API_KEY" : var.govuk_notify_api_key,
    "SENTRY_DSN" : var.sentry_dsn,
    "SLACK_NOTIFICATION_URL" : var.slack_url
    "ELASTIC__API_KEY" : var.elastic_api_key,
    "ELASTIC__CLOUD_ID" : var.cloud_id,
    "EMBEDDING_OPENAI_API_KEY" : var.embedding_openai_api_key,
    "EMBEDDING_AZURE_OPENAI_ENDPOINT" : var.embedding_azure_openai_endpoint,
  }

  reconstructed_django_secrets = [for k, _ in local.django_app_secrets : { name = k, valueFrom = "${aws_secretsmanager_secret.django-app-secret.arn}:${k}::" }]
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

