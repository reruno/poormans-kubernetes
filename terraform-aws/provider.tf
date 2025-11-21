terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "s3" {
    bucket = "poormans-kubernetes-terraform-state-32412"
    region = "eu-central-1"
    key = "terraform/poormans-kubernetes/terraform.tfstate"
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}
