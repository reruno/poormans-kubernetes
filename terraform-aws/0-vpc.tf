resource "aws_vpc" "poormans_kubernetes" {
  cidr_block = "10.0.0.0/16"
  
  tags = {
    Name = "vpc-pm-k8s"
  }
}

resource "aws_subnet" "public_subnet_a" {
  vpc_id = aws_vpc.poormans_kubernetes.id

  cidr_block = "10.0.1.0/24"

  availability_zone = "eu-central-1a"

  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet-a-pm-k8s"
  }

  depends_on = [ aws_vpc.poormans_kubernetes ]
}

resource "aws_subnet" "private_subnet_b" {
  vpc_id = aws_vpc.poormans_kubernetes.id

  cidr_block = "10.0.2.0/24"

  availability_zone = "eu-central-1b"

  tags = {
    Name = "private-subnet-b-pm-k8s"
  }

  depends_on = [ aws_vpc.poormans_kubernetes ]
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.poormans_kubernetes.id
  tags = {
    Name = "igw-pm-k8s"
  }
}

resource "aws_eip" "natgw_eip" {
  domain = "vpc"

  depends_on = [ aws_internet_gateway.igw ]

  tags = {
    Name = "eip-pm-k8s"
  }
}

resource "aws_nat_gateway" "natgw" {
  subnet_id = aws_subnet.public_subnet_a.id

  allocation_id = aws_eip.natgw_eip.id

  tags = {
    Name = "natgw-pm-k8s"
  }

  depends_on = [ aws_eip.natgw_eip, aws_subnet.public_subnet_a ]
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.poormans_kubernetes.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "public-rt-pm-k8s"
  }
}

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.poormans_kubernetes.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_nat_gateway.natgw.id
  }

  tags = {
    Name = "private-rt-pm-k8s"
  }
}

resource "aws_route_table_association" "public_assoc" {
    subnet_id = aws_subnet.public_subnet_a.id
    route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "private_assoc" {
    subnet_id = aws_subnet.private_subnet_b.id
    route_table_id = aws_route_table.private_rt.id
}