variable "cloud" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "db_name" { type = string }
variable "db_username" { type = string }
variable "instance_class" { type = string }
variable "allocated_storage" { type = number }
variable "multi_az" { type = bool }
variable "backup_retention" { type = number }

locals {
  create_aws = var.cloud == "aws" && length(var.subnet_ids) > 0
}

resource "aws_db_subnet_group" "this" {
  count      = local.create_aws ? 1 : 0
  name       = "cs2-${var.environment}"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "db" {
  count       = local.create_aws ? 1 : 0
  name        = "cs2-${var.environment}-db"
  description = "Postgres access from k8s nodes"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
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

resource "aws_db_parameter_group" "pg16" {
  count  = local.create_aws ? 1 : 0
  name   = "cs2-${var.environment}-pg16"
  family = "postgres16"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
}

resource "aws_db_instance" "this" {
  count                       = local.create_aws ? 1 : 0
  identifier                  = "cs2-${var.environment}"
  engine                      = "postgres"
  engine_version              = "16.4"
  instance_class              = var.instance_class
  allocated_storage           = var.allocated_storage
  max_allocated_storage       = var.allocated_storage * 4
  storage_encrypted           = true
  storage_type                = "gp3"
  db_name                     = var.db_name
  username                    = var.db_username
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.this[0].name
  vpc_security_group_ids      = [aws_security_group.db[0].id]
  parameter_group_name        = aws_db_parameter_group.pg16[0].name
  multi_az                    = var.multi_az
  backup_retention_period     = var.backup_retention
  backup_window               = "03:00-04:00"
  maintenance_window          = "Mon:04:30-Mon:05:30"
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  monitoring_interval         = 60
  deletion_protection         = var.environment == "production"
  skip_final_snapshot         = var.environment != "production"
  final_snapshot_identifier   = var.environment == "production" ? "cs2-${var.environment}-final" : null
  apply_immediately           = var.environment != "production"
}

output "endpoint" {
  value     = length(aws_db_instance.this) > 0 ? aws_db_instance.this[0].endpoint : ""
  sensitive = true
}

output "master_password_secret_arn" {
  value     = length(aws_db_instance.this) > 0 ? aws_db_instance.this[0].master_user_secret[0].secret_arn : ""
  sensitive = true
}
