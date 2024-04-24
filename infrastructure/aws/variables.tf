variable "account_id" {
  type        = string
  description = "AWS Account ID"
}

variable "region" {
  type        = string
  default     = "eu-west-2"
  description = "AWS region"
}

variable "state_bucket" {
  type        = string
  description = "Name of the S3 bucket to use a terraform state"
}

variable "image_tag" {
  type        = string
  description = "Image tag"
}

variable "env" {
  type        = string
  description = "Environment"
}

variable "ecr_repository_uri" {
  type        = string
  description = "ECR repo uri"
}

variable "hosted_zone_id" {
  type        = string
  description = "Route 53 Hosted Zone"
}

variable "project_name" {
  type        = string
  description = "Name of project"
}

variable "elastic_api_key" {
  type        = string
  description = "API Key for elastic cloud instance"
}

variable "cloud_id" {
  type        = string
  description = "Cloud ID for elastic cloud instance"
}

variable "django_secret_key" {
  type        = string
  description = "cryptographic signature for djamngo app"
}

variable "postgres_password" {
  type        = string
  description = "postgres password"
}

variable "developer_ips" {
  type        = list(string)
  description = "List of developer IPs"
}

variable "external_ips" {
  type        = list(string)
  description = "List of external IPs"
}

variable "internal_ips" {
  type        = list(string)
  description = "IP's of No10 and CO"
}


variable "openai_api_key" {
  type        = string
  sensitive   = true
  description = "OPENAI api key"
}
variable "rules" {
  description = "The rules to add to this WAF"
  type        = list(object({}))
  default     = []
}

variable "use_case" {
  description = "Use case/resource for WAF"
  type        = string
  default     = "load_balancer"
}

variable "scope" {
  description = "Scope of the WAF, either 'CLOUDFRONT' or 'REGIONAL'"
  type        = string
  default     = "REGIONAL"
}

variable "universal_tags" {
  type        = map(string)
  description = "Map to tag resources with"
}
