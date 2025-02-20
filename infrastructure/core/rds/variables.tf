variable "db_name" {
  type        = string
  description = "Name for the default database attached to the RDS instance"
}

variable "domain_name" {
  type        = string
  description = "Domain name for Database e.g. <organisation>.getrapid.link."
}

variable "instance_type" {
  type        = string
  description = "Instance type name for RDS"
  default     = "db.t3.micro"
}

variable "kms_secrets_arn" {
  type        = string
  description = "ARN of KMS key for secret encryption."
}

variable "name" {
  type        = string
  description = "The name that will be used as a prefix and to identify resources"
}

variable "private_subnet_ids_list" {
  type        = list(string)
  description = "Private Subnet IDs for resource allocation."
}

variable "public_subnet_ids_list" {
  type        = list(string)
  description = "Public Subnet IDs for resource allocation."
}

variable "publicly_accessible" {
  type        = bool
  description = "A flag to indicate if the database should be publicly accessible or not"
  default     = false
}

variable "secret_tags" {
  type        = map(string)
  description = "Tags to apply to the secrets"
  default     = {}
}

variable "securelist_ips" {
  type        = list(string)
  description = "An IP securelist for Database access"
  default     = []
}

variable "service_sg_ids" {
  description = "List of source security group IDs"
  type        = list(string)
}

variable "state_bucket" {
  type        = string
  description = "Name of the S3 bucket to use for terraform state"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for resources to be assigned to."
}

variable "vpc_source_ips" {
  type        = list(string)
  description = "A list of the the private CIDR blocks that should be allowed access to the db."
  default     = ["10.0.0.0/16", "10.73.0.0/16", "10.105.0.0/16"]
}

variable "username" {
  type        = string
  description = "Username for the default database attached to the RDS instance"
  default     = "postgres"
  sensitive   = true
}

variable "password_override_special" {
  type        = string
  default     = "*{}<=()[]"
}

variable "password_min_special" {
  type        = number
  default     = 0
}

variable "password_use_special" {
  type        = bool
  default     = false
}

variable "password_keeper" {
  type        = map
  default     = {
    password_version = 2
  }
}