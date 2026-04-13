variable "cloud" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "node_type" { type = string }

locals {
  create_aws = var.cloud == "aws" && length(var.subnet_ids) > 0
}

resource "aws_elasticache_subnet_group" "this" {
  count      = local.create_aws ? 1 : 0
  name       = "cs2-${var.environment}"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "redis" {
  count  = local.create_aws ? 1 : 0
  name   = "cs2-${var.environment}-redis"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_parameter_group" "this" {
  count  = local.create_aws ? 1 : 0
  name   = "cs2-${var.environment}-redis7"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}

resource "aws_elasticache_replication_group" "this" {
  count                      = local.create_aws ? 1 : 0
  replication_group_id       = "cs2-${var.environment}"
  description                = "cs2-analytics ${var.environment} cache"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.node_type
  num_cache_clusters         = var.environment == "production" ? 2 : 1
  parameter_group_name       = aws_elasticache_parameter_group.this[0].name
  subnet_group_name          = aws_elasticache_subnet_group.this[0].name
  security_group_ids         = [aws_security_group.redis[0].id]
  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled           = var.environment == "production"
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  snapshot_retention_limit   = 7
}

output "endpoint" {
  value = local.create_aws ? aws_elasticache_replication_group.this[0].primary_endpoint_address : ""
}
