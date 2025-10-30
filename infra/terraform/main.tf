terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
  }

  backend "s3" {
    bucket = var.terraform_state_bucket
    key    = "trading-system/terraform.tfstate"
    region = var.aws_region
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "autonomous-trading-system"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# VPC and networking
module "vpc" {
  source = "./modules/vpc"
  
  environment          = var.environment
  vpc_cidr            = var.vpc_cidr
  availability_zones  = data.aws_availability_zones.available.names
  private_subnets     = var.private_subnets
  public_subnets      = var.public_subnets
}

# EKS cluster
module "eks" {
  source = "./modules/eks"
  
  environment         = var.environment
  cluster_name        = "${var.project_name}-${var.environment}"
  cluster_version     = var.kubernetes_version
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  node_groups        = var.node_groups
}

# RDS database
module "rds" {
  source = "./modules/rds"
  
  environment        = var.environment
  vpc_id            = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  database_name     = var.database_name
  database_username = var.database_username
  instance_class    = var.rds_instance_class
  allocated_storage = var.rds_allocated_storage
}

# ElastiCache Redis
module "redis" {
  source = "./modules/redis"
  
  environment        = var.environment
  vpc_id            = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  node_type         = var.redis_node_type
  num_cache_nodes   = var.redis_num_nodes
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  
  environment       = var.environment
  vpc_id           = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  certificate_arn  = var.ssl_certificate_arn
}

# Monitoring and logging
module "monitoring" {
  source = "./modules/monitoring"
  
  environment    = var.environment
  cluster_name   = module.eks.cluster_name
  log_retention_days = var.log_retention_days
}

# Secrets management
module "secrets" {
  source = "./modules/secrets"
  
  environment = var.environment
  secrets = {
    database_password = var.database_password
    api_keys         = var.api_keys
    jwt_secret       = var.jwt_secret
  }
}