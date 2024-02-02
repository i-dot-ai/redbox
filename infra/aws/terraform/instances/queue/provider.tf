terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "5.32.1"
    }
  }

  required_version = "1.6.6"
}

provider "aws" {
  region = "eu-west-2"
}
