resource "aws_security_group" "allow_ssh_external" {
  name        = "allow-ssh-sg"
  description = "Allow SSH inbound traffic"
  
  vpc_id      = aws_subnet.public_subnet_a.vpc_id 

  ingress {
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    
    cidr_blocks = ["0.0.0.0/0"] 
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" 
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sg-allow-ssh-pm-k8s"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }

  depends_on = [ aws_subnet.public_subnet_a ]
}

resource "aws_security_group" "allow_http_external" {
  name        = "allow_http_external"
  description = "Allow inbound HTTP traffic from the internet"
  vpc_id      = aws_subnet.public_subnet_a.vpc_id 

  # Inbound Rule: Allow HTTP (Port 80) from anywhere
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound Rule: Allow all traffic to leave the instance
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow_http_external"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }
}
resource "aws_security_group" "allow_all_external" {
  name        = "allow_all_external"
  description = "Allow all inbound and outbound traffic"
  vpc_id      = aws_subnet.public_subnet_a.vpc_id   # Replace with your VPC ID or resource reference

  # Inbound Rule: Allow everything
  ingress {
    description = "Allow all inbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"  # "-1" is the semantic equivalent of "all protocols"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound Rule: Allow everything
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow_all_external"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }
}
resource "aws_security_group" "allow_ssh_internal" {
  name        = "allow-ssh-from-vpc-sg"
  description = "Allow SSH inbound traffic from VPC"
  
  vpc_id      = aws_vpc.poormans_kubernetes.id 

  ingress {
    description = "SSH from VPC"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    
    cidr_blocks = ["10.0.0.0/16"] 
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" 
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sg-allow-ssh-from-vpc-pm-k8s"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }

  depends_on = [ aws_subnet.private_subnet_b ]
}

resource "aws_security_group" "allow_ping_internal" {
  name        = "allow-ping-internal-sg"
  description = "Allow ICMP (Ping) only within the VPC"
  
  # Assuming aws_vpc.poormans_kubernetes is your VPC resource
  vpc_id      = aws_vpc.poormans_kubernetes.id 

  # Ingress: Allow ICMP from the entire VPC CIDR
  ingress {
    description = "Allow Ping (ICMP) from VPC (10.0.0.0/16)"
    # ICMP type and code are set to -1 to cover all ICMP types and codes
    from_port   = -1 
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["10.0.0.0/16"] 
  }

  # Egress: Allow all outbound traffic (default best practice)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" 
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sg-allow-ping-internal-pm-k8s"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }
}

resource "aws_security_group" "allow_grpc_internal" {
  name        = "allow-grpc-internal-sg"
  description = "Allow Kubernetes API (6443) only within the VPC"
  
  # Assuming aws_vpc.poormans_kubernetes is your VPC resource
  vpc_id      = aws_vpc.poormans_kubernetes.id 

  # Ingress: Allow TCP 6443 from the entire VPC CIDR
  ingress {
    description = "Kubernetes API Server (6443) from VPC (10.0.0.0/16)"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"] 
  }

  # Egress: Allow all outbound traffic (default best practice)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" 
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sg-allow-grpc-internal-pm-k8s"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }
}

resource "aws_security_group" "allow_all_internal" {
  name        = "allow-all-internal-sg"
  description = "Allows all protocols/ports inbound from the VPC CIDR"
  
  # IMPORTANT: Replace aws_vpc.poormans_kubernetes.id with the actual ID 
  # of your VPC resource reference.
  vpc_id      = aws_vpc.poormans_kubernetes.id 

  # --- INGRESS RULE ---
  # Allows all traffic (all protocols, all ports) from the entire VPC CIDR (e.g., 10.0.0.0/16)
  ingress {
    description = "Allow all traffic from VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # Represents ALL protocols (TCP, UDP, ICMP, etc.)
    # Replace the CIDR block if your VPC CIDR is different (e.g., 172.31.0.0/16)
    cidr_blocks = ["10.0.0.0/16"] 
  }

  # --- EGRESS RULE ---
  # Allows all outbound traffic to anywhere (default rule for most AWS SGs)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # ALL protocols
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "sg-allow-all-internal-pm-k8s"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }
}

resource "aws_key_pair" "my_key" {
  key_name = "my-aws-key-pair" 
  public_key = file("~/.ssh/id_ed25519.pub") 
}

# "ami-0f439e819ba112bd7" # Debian amd64
# "ami-0bdbe4d582d76c8ca" # Debian arm64
resource "aws_instance" "public_instance_1" {
  ami           = "ami-0f439e819ba112bd7"  
  instance_type = "t3a.medium"
  subnet_id     = aws_subnet.public_subnet_a.id

  key_name = aws_key_pair.my_key.key_name 

  vpc_security_group_ids = [
    aws_security_group.allow_ssh_external.id,
    aws_security_group.allow_http_external.id,
    aws_security_group.allow_all_external.id,
    aws_security_group.allow_ssh_internal.id,
    aws_security_group.allow_all_internal.id,
  ]

  iam_instance_profile = aws_iam_instance_profile.node_profile.id

  tags = {
    Name = "public-instance-1-pm-k8s"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" 
    http_put_response_hop_limit = 2          
  }

  depends_on = [ 
    aws_security_group.allow_ssh_external,
    aws_security_group.allow_http_external,
    aws_security_group.allow_all_external,
    aws_security_group.allow_ssh_internal,
    aws_security_group.allow_all_internal,
  ]
}

resource "aws_instance" "private_instance_1" {
  ami           = "ami-0f439e819ba112bd7"  
  instance_type = "t3a.small"
  subnet_id     = aws_subnet.private_subnet_b.id

  key_name = aws_key_pair.my_key.key_name 

  vpc_security_group_ids = [
    aws_security_group.allow_ssh_internal.id,
    aws_security_group.allow_all_internal.id,
    aws_security_group.allow_all_external.id,
  ]

  iam_instance_profile = aws_iam_instance_profile.node_profile.id

  tags = {
    Name = "private-instance-1-pm-k8s"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" 
    http_put_response_hop_limit = 2          
  }

  depends_on = [ 
    aws_security_group.allow_ssh_internal,
    aws_security_group.allow_all_internal,
    aws_security_group.allow_all_external,
  ]
}

resource "aws_instance" "private_instance_2" {
  ami           = "ami-0f439e819ba112bd7"  
  instance_type = "t3a.small"
  subnet_id     = aws_subnet.private_subnet_b.id

  key_name = aws_key_pair.my_key.key_name 

  vpc_security_group_ids = [
    aws_security_group.allow_ssh_internal.id,
    aws_security_group.allow_all_internal.id,
    aws_security_group.allow_all_external.id,
  ]

  iam_instance_profile = aws_iam_instance_profile.node_profile.id

  tags = {
    Name = "private-instance-2-pm-k8s"
    "kubernetes.io/cluster/${local.cluster_name}" = "owned"
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" 
    http_put_response_hop_limit = 2          
  }

  depends_on = [ 
    aws_security_group.allow_ssh_internal,
    aws_security_group.allow_all_internal,
    aws_security_group.allow_all_external,
  ]
}