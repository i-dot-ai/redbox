variable "account_id" {
  type        = string
  description = "AWS Account ID"
}

variable "cloud_id" {
  type        = string
  description = "Cloud ID for elastic cloud instance"
}

variable "cognito_usernames" {
  type        = list(string)
  description = "List of usernames to be added"
  default     = []
}

variable "contact_email" {
  description = "The email to use for 'contact us' pages"
  type        = string
}

variable "developer_ips" {
  type        = list(string)
  description = "List of developer IPs"
}

variable "django_command" {
  type = list(object({
    command : string,
    task_name : string,
    schedule : optional(string),
  }))
  default = [
    { command : "delete_expired_data", task_name : "delete", schedule : "cron(00 02 * * ? *)" }, # every day at 2-2:30am
    { command : "reingest_files", task_name : "reingest" }                                       # manually triggered
  ]
  description = "An object describing the django command to run"
}

variable "django_secret_key" {
  type        = string
  description = "cryptographic signature for django app"
}

variable "domain_name" {
  type        = string
  description = "The base domain name for the project"
}

variable "ecr_repository_uri" {
  type        = string
  description = "ECR repo uri"
}

variable "elastic_api_key" {
  type        = string
  description = "API Key for elastic cloud instance"
}

variable "env" {
  type        = string
  description = "Environment"
}

variable "external_ips" {
  type        = list(string)
  description = "List of external IPs"
}

variable "from_email" {
  type        = string
  sensitive   = true
  description = "GOV notify from email"
}

variable "govuk_notify_plain_email_template_id" {
  type        = string
  sensitive   = true
  description = "GOV notify plain template id"
}

variable "govuk_notify_api_key" {
  type        = string
  sensitive   = true
  description = "GOV notify API key"
}

variable "hosted_zone_id" {
  type        = string
  description = "Route 53 Hosted Zone"
}

variable "image_tag" {
  type        = string
  description = "Image tag"
}

variable "internal_ips" {
  type        = list(string)
  description = "IP's of No10 and CO"
}

variable "embedding_openai_api_key" {
  type        = string
  sensitive   = true
  default     = null
  description = "OPENAI api key"
}

variable "embedding_azure_openai_endpoint" {
  type        = string
  default     = null
  description = "The base URL for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_model" {
  type        = string
  default     = "gpt-3.5-turbo"
  description = "OPENAI model to use"
}


variable "openai_api_version_35t" {
  type        = string
  default     = "2023-12-01-preview"
  description = "OPENAI API version"
}

variable "azure_openai_api_key_35t" {
  type        = string
  sensitive   = true
  default     = null
  description = "The API key for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_fallback_api_key_35t" {
  type        = string
  sensitive   = true
  default     = null
  description = "The API key for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_endpoint_35t" {
  type        = string
  default     = null
  description = "The base URL for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_fallback_endpoint_35t" {
  type        = string
  default     = null
  description = "The base URL for your fallback Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "openai_api_version_4t" {
  type        = string
  default     = "2023-12-01-preview"
  description = "OPENAI API version"
}

variable "azure_openai_api_key_4t" {
  type        = string
  sensitive   = true
  default     = null
  description = "The API key for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_fallback_api_key_4t" {
  type        = string
  sensitive   = true
  default     = null
  description = "The API key for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_endpoint_4t" {
  type        = string
  default     = null
  description = "The base URL for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_fallback_endpoint_4t" {
  type        = string
  default     = null
  description = "The base URL for your fallback Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "openai_api_version_4o" {
  type        = string
  default     = "2023-12-01-preview"
  description = "OPENAI API version"
}

variable "azure_openai_api_key_4o" {
  type        = string
  sensitive   = true
  default     = null
  description = "The API key for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_fallback_api_key_4o" {
  type        = string
  sensitive   = true
  default     = null
  description = "The API key for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_endpoint_4o" {
  type        = string
  default     = null
  description = "The base URL for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_fallback_endpoint_4o" {
  type        = string
  default     = null
  description = "The base URL for your fallback Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "project_name" {
  type        = string
  description = "Name of project"
}

variable "region" {
  type        = string
  default     = "eu-west-2"
  description = "AWS region"
}

variable "rules" {
  description = "The rules to add to this WAF"
  type        = list(object({}))
  default     = []
}

variable "sentry_dsn" {
  description = "The sentry dsn to send sentry logs to"
  type        = string
  default     = null
}

variable "sentry_environment" {
  description = "The sentry environment to send sentry logs to"
  type        = string
  default     = null
}

variable "sentry_report_to_endpoint" {
  description = "The sentry endpoint to which the Report-To header should refer"
  type        = string
  default     = null
}

variable "scope" {
  description = "Scope of the WAF, either 'CLOUDFRONT' or 'REGIONAL'"
  type        = string
  default     = "REGIONAL"
}

variable "slack_url" {
  description = "The slack webhook url"
  type        = string
}

variable "state_bucket" {
  type        = string
  description = "Name of the S3 bucket to use a terraform state"
}

variable "universal_tags" {
  type        = map(string)
  description = "Map to tag resources with"
}

variable "use_case" {
  description = "Use case/resource for WAF"
  type        = string
  default     = "load_balancer"
}

variable "team_name" {
  type        = string
  description = "The name of the team"
}

variable "publicly_accessible" {
  type        = bool
  description = "Flag to determine if the database is publicly accessible"
}


variable "embedding_document_field_name" {
  type        = string
  default     = "azure_embedding"
  description = "embedding document field name"
}

variable "embedding_max_retries" {
  type        = number
  default     = 1
  description = "Number of retries to external embedding services (rate limiting)"
}

variable "embedding_retry_min_seconds" {
  type        = number
  default     = 120
  description = "Number of seconds to wait before retry to external embedding services (rate limiting)"
}

variable "embedding_retry_max_seconds" {
  type        = number
  default     = 300
  description = "Maximum number of seconds to wait before retry to external embedding services (rate limiting)"
}

variable "worker_ingest_min_chunk_size" {
  type        = number
  default     = 1000
  description = "Normal chunk resolution. Minimum size of chunks to be produced by the worker"
}

variable "worker_ingest_max_chunk_size" {
  type        = number
  default     = 10000
  description = "Normal chunk resolution. Maximum size of chunks to be produced by the worker"
}

variable "worker_ingest_largest_chunk_size" {
  type        = number
  default     = 300000
  description = "Largest chunk resolution. Maximum size of chunks to be produced by the worker"
}

variable "worker_ingest_largest_chunk_overlap" {
  type        = number
  default     = 0
  description = "Largest chunk resolution. Size of overlap between chunks produced by the worker"
}

variable "django_queue_timeout" {
  type        = number
  default     = 300
  description = "How long to wait for unstructured to complete task"
}

variable "django_queue_retry" {
  type        = number
  default     = 300
  description = "How long to wait between retrying unstructured task"
}

variable "django_queue_max_attempts" {
  type        = number
  default     = 1
  description = "How many attempts to run unstructured task"
}

variable "embedding_backend" {
  type        = string
  default     = "text-embedding-3-large"
  description = "which provider to use to embed text, e.g. azure, aws, openai"
}

