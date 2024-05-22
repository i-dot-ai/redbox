locals {
  record_prefix = terraform.workspace == "prod" ? var.project_name : "${var.project_name}-${terraform.workspace}"
  django_host   = "${local.record_prefix}.${var.domain_name}"

  environment_variables = {
    "ELASTIC__API_KEY" : var.elastic_api_key,
    "ELASTIC__CLOUD_ID" : var.cloud_id,
    "OBJECT_STORE" : "s3",
    "BUCKET_NAME" : aws_s3_bucket.user_data_bucket.bucket,
    "EMBEDDING_MODEL" : "all-mpnet-base-v2",
    "EMBED_QUEUE_NAME" : "redbox-embedder-queue",
    "INGEST_QUEUE_NAME" : "redbox-ingester-queue",
    "REDIS_HOST" : module.elasticache.redis_address,
    "REDIS_PORT" : module.elasticache.redis_port,
    "ENVIRONMENT" : upper(terraform.workspace),
    "DEBUG" : true,
    "AWS_REGION" : var.region,
    "OPENAI_API_KEY" : var.openai_api_key,
    "USE_STREAMING" : false,
  }
}

module "cluster" {
  source         = "../../../i-ai-core-infrastructure//modules/ecs_cluster"
  project_prefix = var.project_name
  name           = "${terraform.workspace}-${var.project_name}"
}

resource "aws_service_discovery_private_dns_namespace" "private_dns_namespace" {
  name        = "internal"
  description = "redbox private dns namespace"
  vpc         = data.terraform_remote_state.vpc.outputs.vpc_id
}

resource "aws_service_discovery_service" "service_discovery_service" {
  name = "core-api"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.private_dns_namespace.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

module "core_api" {
  service_discovery_service_arn = aws_service_discovery_service.service_discovery_service.arn
  memory                        = 4096
  cpu                           = 2048
  create_listener               = false
  create_networking             = false
  source                        = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name                  = "core-api"
  image_tag                     = var.image_tag
  prefix                        = "redbox"
  ecr_repository_uri            = "${var.ecr_repository_uri}/redbox-core-api"
  ecs_cluster_id                = module.cluster.ecs_cluster_id
  health_check = {
    healthy_threshold   = 3
    unhealthy_threshold = 3
    accepted_response   = "200"
    path                = "/health"
    timeout             = 5
  }
  state_bucket                 = var.state_bucket
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  container_port               = 5002
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ip_whitelist                 = var.external_ips
  environment_variables        = local.environment_variables
}


module "worker" {
  memory             = 6144
  cpu                = 2048
  create_listener    = false
  create_networking  = false
  source             = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name       = "worker"
  image_tag          = var.image_tag
  prefix             = "redbox"
  ecr_repository_uri = "${var.ecr_repository_uri}/redbox-worker"
  ecs_cluster_id     = module.cluster.ecs_cluster_id
  state_bucket                 = var.state_bucket
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  container_port               = 5000
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ip_whitelist                 = var.external_ips
  environment_variables        = local.environment_variables
  http_healthcheck = false
}
