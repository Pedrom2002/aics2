variable "cloud" { type = string }
variable "environment" { type = string }
variable "cluster_name" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "node_count" { type = number }
variable "node_size" { type = string }

locals {
  create_eks = var.cloud == "aws" && length(var.subnet_ids) > 0
}

module "eks" {
  count   = local.create_eks ? 1 : 0
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.24"

  cluster_name    = var.cluster_name
  cluster_version = "1.30"

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  vpc_id                   = var.vpc_id
  subnet_ids               = var.subnet_ids
  control_plane_subnet_ids = var.subnet_ids

  enable_cluster_creator_admin_permissions = true
  enable_irsa                              = true

  cluster_addons = {
    coredns                = { most_recent = true }
    kube-proxy             = { most_recent = true }
    vpc-cni                = { most_recent = true }
    aws-ebs-csi-driver     = { most_recent = true }
    eks-pod-identity-agent = { most_recent = true }
  }

  eks_managed_node_groups = {
    default = {
      min_size     = max(2, floor(var.node_count / 2))
      max_size     = var.node_count * 2
      desired_size = var.node_count
      instance_types = [var.node_size]
      capacity_type  = "ON_DEMAND"
      labels = {
        role = "app"
      }
    }
  }
}

# Bootstrap helm add-ons post-cluster
provider "kubernetes" {
  host                   = local.create_eks ? module.eks[0].cluster_endpoint : ""
  cluster_ca_certificate = local.create_eks ? base64decode(module.eks[0].cluster_certificate_authority_data) : ""
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = local.create_eks ? module.eks[0].cluster_endpoint : ""
    cluster_ca_certificate = local.create_eks ? base64decode(module.eks[0].cluster_certificate_authority_data) : ""
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
    }
  }
}

resource "helm_release" "cert_manager" {
  count            = local.create_eks ? 1 : 0
  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  version          = "v1.16.2"
  namespace        = "cert-manager"
  create_namespace = true
  set {
    name  = "installCRDs"
    value = "true"
  }
  depends_on = [module.eks]
}

resource "helm_release" "external_secrets" {
  count            = local.create_eks ? 1 : 0
  name             = "external-secrets"
  repository       = "https://charts.external-secrets.io"
  chart            = "external-secrets"
  version          = "0.10.4"
  namespace        = "external-secrets"
  create_namespace = true
  depends_on       = [module.eks]
}

resource "helm_release" "kube_prometheus_stack" {
  count            = local.create_eks ? 1 : 0
  name             = "kube-prometheus-stack"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = "65.1.0"
  namespace        = "monitoring"
  create_namespace = true
  values = [yamlencode({
    grafana = {
      adminPassword = "change-me-via-external-secret"
      sidecar = { dashboards = { enabled = true, label = "grafana_dashboard" } }
    }
  })]
  depends_on = [module.eks]
}

resource "helm_release" "loki_stack" {
  count            = local.create_eks ? 1 : 0
  name             = "loki"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "loki-stack"
  version          = "2.10.2"
  namespace        = "monitoring"
  create_namespace = true
  values = [yamlencode({
    promtail = { enabled = true }
    grafana  = { enabled = false }
  })]
  depends_on = [helm_release.kube_prometheus_stack]
}

output "cluster_endpoint" {
  value = local.create_eks ? module.eks[0].cluster_endpoint : ""
}

output "cluster_name" {
  value = var.cluster_name
}

output "cluster_oidc_issuer_url" {
  value = local.create_eks ? module.eks[0].cluster_oidc_issuer_url : ""
}
