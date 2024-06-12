data "terraform_remote_state" "redbox" {
  backend   = "s3"
  workspace = terraform.workspace
  config = {
    bucket = var.state_bucket
    key    = "redboc/terraform.tfstate"
    region = var.region
  }
}

provider "aws" {
  default_tags {
    tags = {
      Environment = terraform.workspace
      Deployed    = "github"
    }
  }
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.53.0"
    }

    random = {
      source  = "hashicorp/random"
      version = ">=3.6.2"
    }
  }
  required_version = ">= 1.3.5"

  backend "s3" {
    key = "redbox/terraform.tfstate"
  }

}
