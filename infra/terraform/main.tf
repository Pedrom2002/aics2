###############################################################################
# CS2 Analytics — Terraform root module (SCAFFOLDING).
#
# This is intentionally minimal. It wires up provider configuration and module
# stubs. Each module under modules/ contains placeholder resources with TODO
# comments — production use requires filling in IAM, networking, backups,
# monitoring, etc.
#
# Recommended workflow:
#   terraform init
#   terraform workspace new staging
#   terraform plan -var-file=staging.tfvars
#   terraform apply -var-file=staging.tfvars
###############################################################################

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 6.10"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.33"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.16"
    }
  }

  backend "s3" {
    bucket         = "cs2-analytics-tfstate"
    key            = "global/terraform.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "cs2-analytics-tflock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "cs2-analytics"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

###############################################################################
# Modules
###############################################################################

module "vpc" {
  source = "./modules/vpc"

  cloud       = var.cloud
  environment = var.environment
  cidr_block  = var.vpc_cidr
}

module "rds" {
  source = "./modules/rds"

  cloud              = var.cloud
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  db_name            = "cs2analytics"
  db_username        = "cs2user"
  instance_class     = var.rds_instance_class
  allocated_storage  = var.rds_allocated_storage
  multi_az           = var.environment == "production"
  backup_retention   = 14
}

module "redis" {
  source = "./modules/redis"

  cloud         = var.cloud
  environment   = var.environment
  vpc_id        = module.vpc.vpc_id
  subnet_ids    = module.vpc.private_subnet_ids
  node_type     = var.redis_node_type
}

module "k8s" {
  source = "./modules/k8s"

  cloud           = var.cloud
  environment     = var.environment
  cluster_name    = "cs2-analytics-${var.environment}"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids
  node_count      = var.k8s_node_count
  node_size       = var.k8s_node_size
}

###############################################################################
# Outputs
###############################################################################

output "k8s_cluster_endpoint" {
  value = module.k8s.cluster_endpoint
}

output "rds_endpoint" {
  value     = module.rds.endpoint
  sensitive = true
}

output "redis_endpoint" {
  value = module.redis.endpoint
}
