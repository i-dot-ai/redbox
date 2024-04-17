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

variable "project_name" {
  type        = string
  description = "Name of the project"
}

variable "env" {
  type        = string
  description = "Environment"
}

