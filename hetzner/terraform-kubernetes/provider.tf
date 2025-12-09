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
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = ">= 1.14.0"
    }
    # Added: Required for fetching the YAML from the URL
    http = {
      source  = "hashicorp/http"
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
    config_path = var.kube_config_path
  }
}

provider "kubernetes" {
  config_path = var.kube_config_path
}

provider "kubectl" {
  config_path = var.kube_config_path
}