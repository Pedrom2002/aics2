# Kubernetes (EKS / GKE) module — SCAFFOLDING.

variable "cloud" { type = string }
variable "environment" { type = string }
variable "cluster_name" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "node_count" { type = number }
variable "node_size" { type = string }

# AWS path: use terraform-aws-modules/eks/aws.
# GCP path: use terraform-google-modules/kubernetes-engine/google.
#
# TODO:
# - OIDC provider for IRSA / workload identity
# - cluster autoscaler / karpenter
# - aws-load-balancer-controller / gke ingress
# - external-dns + cert-manager bootstrap (helm_release)
# - prometheus + grafana stack (kube-prometheus-stack)
# - log shipping to CloudWatch / Cloud Logging

output "cluster_endpoint" {
  value = "TODO-cluster-endpoint"
}

output "cluster_name" {
  value = var.cluster_name
}
