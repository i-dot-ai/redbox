variable "project_name" {
  type        = string
  description = "Name of project"
}

variable "team_name" {
  type        = string
  description = "The name of the team"
}

variable "region" {
  type        = string
  description = "aws region"
  default     = "eu-west-2"
}

variable "state_bucket" {
  type        = string
  description = "Name of the S3 bucket to use a terraform state"
}
