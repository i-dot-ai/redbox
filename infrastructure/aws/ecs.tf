locals {
  host        = terraform.workspace == "prod" ? "${var.project_name}.ai.cabinetoffice.gov.uk" : "${var.project_name}-${terraform.workspace}.ai.cabinetoffice.gov.uk"
  prefix      = "backend"
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
    "DJANGO_SECRET_KEY" : var.django_secret_key,
    "POSTGRES_PASSWORD" : var.postgres_password
  }
}

module "cluster" {
  source         = "../../../i-ai-core-infrastructure//modules/ecs_cluster"
  project_prefix = var.project_name
  name           = "backend"
}

resource "aws_route53_record" "type_a_record" {
  zone_id = var.hosted_zone_id
  name    = local.host
  type    = "A"

  alias {
    name                   = module.load_balancer.load_balancer_dns_name
    zone_id                = module.load_balancer.load_balancer_zone_id
    evaluate_target_health = true
  }
}


module "core_api" {
  create_networking  = true
  create_listener    = true
  source             = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name       = "redbox-core-api"
  image_tag          = var.image_tag
  prefix             = local.prefix
  ecr_repository_uri = "${var.ecr_repository_uri}/redbox-core-api"
  ecs_cluster_id     = module.cluster.ecs_cluster_id
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
  host                         = local.host
  ip_whitelist                 = var.external_ips
  environment_variables        = local.environment_variables
}


module "embedder" {
  create_networking  = false
  memory             = 2048
  cpu                = 1024
  source             = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name       = "redbox-embedder"
  image_tag          = var.image_tag
  prefix             = local.prefix
  ecr_repository_uri = "${var.ecr_repository_uri}/redbox-embedder"
  ecs_cluster_id     = module.cluster.ecs_cluster_id
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
  container_port               = 5000
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  host                         = local.host
  ip_whitelist                 = var.external_ips
  environment_variables        = local.environment_variables
}


module "ingester" {
  create_networking  = false
  memory             = 4096
  cpu                = 2048
  source             = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name       = "redbox-ingester"
  image_tag          = var.image_tag
  prefix             = local.prefix
  ecr_repository_uri = "${var.ecr_repository_uri}/redbox-ingester"
  ecs_cluster_id     = module.cluster.ecs_cluster_id
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
  container_port               = 5000
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  host                         = local.host
  ip_whitelist                 = var.external_ips
  environment_variables        = local.environment_variables
}
