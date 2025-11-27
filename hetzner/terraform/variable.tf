variable "hcloud_token" {
  sensitive = true
  type = string
}

variable "hetzner_zone_domain" {
  type = string # example: "example.com"
}

variable "ssh_public_key_path" {
  sensitive = true
  type = string # example: "example.com"
}