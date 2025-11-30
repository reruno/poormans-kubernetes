variable "metallb_ip" {
  description = "The IP address for MetalLB to assign (CIDR notation), basically it is public ip of a node, this public ip shouldn't be used anywhere expect metallb"
  type        = string # example value is "46.224.86.99/32"
}

variable "acme_email" {
  description = "The email address used for Let's Encrypt registration and expiration warnings."
  type        = string
}

variable "kube_config_path" {
  description = "Path to the kubeconfig file used by the providers"
  type        = string
}

variable "nfs_server_ip" {
  description = "The private IP address of the NFS server (Volume Node)"
  type        = string
}