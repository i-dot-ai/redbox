terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.2.0"
    }
  }
  required_version = ">= 1.3.5"

  backend "s3" {
    key            = "redbox/terraform.tfstate"
    # TODO: Remove this before the end of ticket
    dynamodb_table = "i-dot-ai-dev-dynamo-lock"
  }

}

provider "aws" {
  default_tags {
    tags = {
      Environment = terraform.workspace
    }
  }
}
