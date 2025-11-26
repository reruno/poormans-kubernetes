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
}

provider "helm" {
    kubernetes = {
        config_path = "~/.kube/config"
    }
}

provider "kubernetes" {
    config_path = "~/.kube/config"
}
provider "kubectl" {
    config_path = "~/.kube/config"
}