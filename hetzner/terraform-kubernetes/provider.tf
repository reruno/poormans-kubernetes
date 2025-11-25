terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.0.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.0.0"
    }
  }
  backend "s3" {
    bucket = "poormans-kubernetes-terraform-state-32412"
    region = "eu-central-1"
    key = "terraform/poormans-kubernetes/terraform-hetzner-kubernetes.tfstate"
  }
}

provider "helm" {
    kubernetes = {
        config_path = "~/.kube/config"
    }
}

provider "kubernetes" {
    config_path = "~/.kube/config"
}