resource "aws_iam_policy" "node_policy" {
    name        = "pm-k8s-node-policy"
    description = "Policy for Kubernetes Worker Nodes"

    policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # --- 1. CORE KUBERNETES & KUBELET ---
      {
        Sid      = "KubeletInstanceAndECR",
        Effect   = "Allow",
        Action   = [
          "ec2:DescribeInstances",
          "ec2:DescribeRegions",
          "ec2:DescribeTags",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:DescribeRepositories",
          "ecr:ListImages",
          "ecr:BatchGetImage"
        ],
        Resource = "*"
      },

      # --- 2. AWS LOAD BALANCER CONTROLLER (ALB/NLB) ---
      # This allows the pod to create/delete Load Balancers and manage Security Groups for them.
      {
        Sid      = "AWSLoadBalancerController",
        Effect   = "Allow",
        Action   = [
          "elasticloadbalancing:*", 
          "ec2:DescribeAccountAttributes",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeAddresses",
          "ec2:DescribeInternetGateways",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeNetworkInterfaces",
          "ec2:CreateSecurityGroup",
          "ec2:RevokeSecurityGroupIngress",
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:CreateTags",
          "ec2:DeleteTags",
          "ec2:DeleteSecurityGroup",
          "cognito-idp:DescribeUserPoolClient",
          "acm:ListCertificates",
          "acm:DescribeCertificate",
          "iam:ListServerCertificates",
          "iam:GetServerCertificate",
          "waf-regional:GetWebACL",
          "waf-regional:GetWebACLForResource",
          "waf-regional:AssociateWebACL",
          "waf-regional:DisassociateWebACL",
          "wafv2:GetWebACL",
          "wafv2:GetWebACLForResource",
          "wafv2:AssociateWebACL",
          "wafv2:DisassociateWebACL",
          "shield:GetSubscriptionState",
          "shield:DescribeProtection",
          "shield:CreateProtection",
          "shield:DeleteProtection"
        ],
        Resource = "*"
      },

      # --- 3. CLOUD CONTROLLER MANAGER (Node Discovery) ---
      # If you run the Cloud Controller Manager, it needs to tag instances.
      {
        Sid      = "CloudControllerManager",
        Effect   = "Allow",
        Action   = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeTags",
          "ec2:ModifyInstanceAttribute",
          "ec2:CreateRoute",
          "ec2:DeleteRoute",
          "ec2:DescribeRouteTables"
        ],
        Resource = "*"
      }
    ]
  })
}

# The Role (Identity)
resource "aws_iam_role" "node_role" {
    name = "pm-k8s-node-role"

    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
        {
            Action = "sts:AssumeRole"
            Effect = "Allow"
            Principal = {
            Service = "ec2.amazonaws.com"
            }
        },
        ]
    })
}

resource "aws_iam_role_policy_attachment" "node_attach" {
    role       = aws_iam_role.node_role.name
    policy_arn = aws_iam_policy.node_policy.arn
}

resource "aws_iam_instance_profile" "node_profile" {
    name = "pm-k8s-node-profile"
    role = aws_iam_role.node_role.name
}