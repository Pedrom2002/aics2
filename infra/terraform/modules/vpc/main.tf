variable "cloud" { type = string }
variable "environment" { type = string }
variable "cidr_block" { type = string }

locals {
  name = "cs2-${var.environment}"
  azs  = ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
}

module "aws_vpc" {
  count   = var.cloud == "aws" ? 1 : 0
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.13"

  name = local.name
  cidr = var.cidr_block
  azs  = local.azs

  private_subnets = [
    cidrsubnet(var.cidr_block, 4, 0),
    cidrsubnet(var.cidr_block, 4, 1),
    cidrsubnet(var.cidr_block, 4, 2),
  ]
  public_subnets = [
    cidrsubnet(var.cidr_block, 4, 8),
    cidrsubnet(var.cidr_block, 4, 9),
    cidrsubnet(var.cidr_block, 4, 10),
  ]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "production"
  enable_dns_hostnames = true
  enable_dns_support   = true

  enable_flow_log                    = true
  create_flow_log_cloudwatch_iam_role = true
  create_flow_log_cloudwatch_log_group = true

  public_subnet_tags  = { "kubernetes.io/role/elb" = "1" }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = "1" }
}

output "vpc_id" {
  value = var.cloud == "aws" ? module.aws_vpc[0].vpc_id : ""
}

output "private_subnet_ids" {
  value = var.cloud == "aws" ? module.aws_vpc[0].private_subnets : []
}

output "public_subnet_ids" {
  value = var.cloud == "aws" ? module.aws_vpc[0].public_subnets : []
}
