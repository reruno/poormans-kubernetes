terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }
  backend "s3" {
    bucket = "poormans-kubernetes-terraform-state-32412"
    region = "eu-central-1"
    key = "terraform/poormans-kubernetes/terraform-hetzner.tfstate"
  }
}

provider "hcloud" {
  token = var.hcloud_token
}