variable "aws_region" {
  description = "The AWS region to deploy resources in."
  type        = string
  default     = "eu-central-1"
}

variable "aws_az_1" {
  description = "The availability zone for public subnet"
  type        = string
  default     = "eu-central-1a"
}

variable "aws_az_2" {
  description = "The availability zone for private subnet"
  type        = string
  default     = "eu-central-1b"
}

variable "ec2_image" {
  type = string
  default = "ami-086508493974ec350" # debian
}

locals {
  cluster_name = "kubernetes" 
}