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

variable "azure_openai_model" {
  type        = string
  default     = "gpt-3.5-turbo"
  description = "OPENAI model to use"
}

variable "openai_api_key" {
  type        = string
  sensitive   = true
  default     = null
  description = "OPENAI api key"
}

variable "openai_api_version" {
  type        = string
  default     = "2023-12-01-preview"
  description = "OPENAI API version"
}

variable "azure_openai_api_key" {
  type        = string
  sensitive   = true
  default     = null
  description = "The API key for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
}

variable "azure_openai_endpoint" {
  type        = string
  default     = null
  description = "The base URL for your Azure OpenAI resource.  You can find this in the Azure portal under your Azure OpenAI resource."
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

variable "scope" {
  description = "Scope of the WAF, either 'CLOUDFRONT' or 'REGIONAL'"
  type        = string
  default     = "REGIONAL"
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
