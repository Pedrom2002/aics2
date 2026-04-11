# Terraform — cs2-analytics

**Status: scaffolding only.** This is a starting point, not production-ready
infrastructure-as-code. Resources are stubbed and most blocks are commented
out with `TODO:` markers.

## Layout

```
infra/terraform/
  main.tf         providers + module wiring
  variables.tf    inputs (cloud, region, sizing)
  modules/
    vpc/          VPC + subnets
    rds/          Postgres
    redis/        ElastiCache / Memorystore
    k8s/          EKS / GKE
```

## Before applying

1. Configure remote state (uncomment the `backend` block in `main.tf`).
2. Decide cloud target via `var.cloud` (`aws` or `gcp`).
3. Create a `staging.tfvars` and `production.tfvars` per environment.
4. Bootstrap secrets out-of-band (AWS Secrets Manager / Google Secret Manager).
5. Fill in the TODO blocks in each module.

## Usage

```bash
cd infra/terraform
terraform init
terraform workspace new staging
terraform plan -var-file=staging.tfvars
terraform apply -var-file=staging.tfvars
```
