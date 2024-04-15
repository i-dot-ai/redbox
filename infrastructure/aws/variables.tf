variable "account_id" {
  type        = string
  description = "AWS Account ID"
}

variable "region" {
  type = string
  default = "eu-west-2"
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
  type = string
  description = "Route 53 Hosted Zone"
}

variable "project_name" {
  type        = string
  description = "Name of project"
}
