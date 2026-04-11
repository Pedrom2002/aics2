# RDS Postgres module — SCAFFOLDING.

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

# TODO: random_password for db, store in secretsmanager, parameter group with
# pg_stat_statements and slow query logging, security group restricted to k8s
# node SG, performance insights, automated snapshot to S3.

resource "aws_db_subnet_group" "this" {
  count      = var.cloud == "aws" && length(var.subnet_ids) > 0 ? 1 : 0
  name       = "cs2-${var.environment}"
  subnet_ids = var.subnet_ids
}

# resource "aws_db_instance" "this" {
#   identifier              = "cs2-${var.environment}"
#   engine                  = "postgres"
#   engine_version          = "16.4"
#   instance_class          = var.instance_class
#   allocated_storage       = var.allocated_storage
#   storage_encrypted       = true
#   db_name                 = var.db_name
#   username                = var.db_username
#   manage_master_user_password = true
#   db_subnet_group_name    = aws_db_subnet_group.this[0].name
#   multi_az                = var.multi_az
#   backup_retention_period = var.backup_retention
#   deletion_protection     = var.environment == "production"
#   skip_final_snapshot     = var.environment != "production"
# }

output "endpoint" {
  value = "TODO-rds-endpoint"
}
