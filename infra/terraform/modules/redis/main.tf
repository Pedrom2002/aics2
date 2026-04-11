# ElastiCache Redis module — SCAFFOLDING.

variable "cloud" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "node_type" { type = string }

# TODO:
# - aws_elasticache_subnet_group
# - aws_elasticache_replication_group with at-rest + in-transit encryption
# - automatic_failover_enabled = true for production
# - parameter group with maxmemory-policy = allkeys-lru
# - SG ingress only from k8s node SG

output "endpoint" {
  value = "TODO-redis-endpoint"
}
