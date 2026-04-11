variable "cloud" {
  description = "Target cloud (aws or gcp)."
  type        = string
  default     = "aws"

  validation {
    condition     = contains(["aws", "gcp"], var.cloud)
    error_message = "cloud must be aws or gcp."
  }
}

variable "environment" {
  description = "Environment name (staging, production)."
  type        = string
  default     = "staging"
}

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "gcp_project" {
  type    = string
  default = ""
}

variable "gcp_region" {
  type    = string
  default = "europe-west1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "rds_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "rds_allocated_storage" {
  type    = number
  default = 100
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "k8s_node_count" {
  type    = number
  default = 3
}

variable "k8s_node_size" {
  type    = string
  default = "t3.large"
}
