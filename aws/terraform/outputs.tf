output "ec2_public_worker_node_1_public_ip" {
  description = "The public IP address of the public_instance_1 instance."
  value       = aws_instance.public_instance_1.public_ip
}

output "ec2_public_worker_node_1_private_ip" {
  description = "The private IP address of the public_instance_1 instance."
  value       = aws_instance.public_instance_1.private_ip
}

output "ec2_private_worker_node_2_private_ip" {
  description = "The private IP address of the private_instance_1 instance."
  value       = aws_instance.private_instance_1.private_ip
}

output "ec2_private_control_plane_private_ip" {
  description = "The private IP address of the private_instance_1 instance."
  value       = aws_instance.private_instance_2.private_ip
}

output "vpc_id" {
  description = "VPC ID of pm k8s."
  value       = aws_vpc.poormans_kubernetes.id
}