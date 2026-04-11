# VPC module — SCAFFOLDING.
# TODO: pin to terraform-aws-modules/vpc/aws or google-modules/network/google.

variable "cloud" { type = string }
variable "environment" { type = string }
variable "cidr_block" { type = string }

# AWS path
resource "aws_vpc" "this" {
  count                = var.cloud == "aws" ? 1 : 0
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "cs2-${var.environment}"
  }
}

# TODO: public/private subnets across 3 AZs, NAT gateways, route tables,
# flow logs, VPC endpoints (S3, ECR, secrets manager), and a bastion or SSM.

output "vpc_id" {
  value = var.cloud == "aws" ? try(aws_vpc.this[0].id, "") : ""
}

output "private_subnet_ids" {
  # TODO: emit real subnet IDs once subnets are defined.
  value = []
}
