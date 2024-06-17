terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.2.0"
    }
  }
  required_version = ">= 1.3.5"

  backend "s3" {
    key = "redbox/terraform.tfstate"
  }

}

provider "aws" {
  default_tags {
    tags = {
      platform:environment = terraform.workspace

      Organisation  = "co"
      Department    = "i-dot-ai"
      "Cost Centre" = "i-dot-ai"
    }
  }
}
