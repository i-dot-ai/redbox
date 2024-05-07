locals {
  record_prefix = terraform.workspace == "prod" ? var.project_name : "${var.project_name}-${terraform.workspace}"
  django_host          = "${local.record_prefix}.${var.domain_name}"
  api_host          = "${local.record_prefix}-api.${var.domain_name}"

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
#     django stuff
    "DJANGO_SECRET_KEY" : var.django_secret_key,
    "POSTGRES_PASSWORD" : var.postgres_password,
    "POSTGRES_USER" : module.rds.rds_instance_username,
    "POSTGRES_PASSWORD": module.rds.rds_instance_db_password,
    "POSTGRES_DB" : module.rds.db_instance_name,
    "POSTGRES_HOST" : module.rds.db_instance_address,
    "CORE_API_HOST" : "https://${local.api_host}",
    "CORE_API_PORT": 8000,
    "ENVIRONMENT": upper(terraform.workspace),
    "DJANGO_SETTINGS_MODULE": "redbox_app.settings",
    "DEBUG": false,
    "AWS_REGION": var.region,
    "OPENAI_API_KEY" : var.openai_api_key,
    "NOTIFY_API_KEY" : var.notify_api_key,
    "FROM_EMAIL" : var.from_email,
    "GOVUK_NOTIFY_API_KEY" : var.govuk_notify_plain_email_template_id,

  }
}

module "cluster" {
  source         = "../../../i-ai-core-infrastructure//modules/ecs_cluster"
  project_prefix = var.project_name
  name           = "backend"
}

resource "aws_route53_record" "type_a_record_core_api" {
  zone_id = var.hosted_zone_id
  name    = local.api_host
  type    = "A"

  alias {
    name                   = module.load_balancer.load_balancer_dns_name
    zone_id                = module.load_balancer.load_balancer_zone_id
    evaluate_target_health = true
  }
}


resource "aws_route53_record" "type_a_record" {
  zone_id = var.hosted_zone_id
  name    = local.django_host
  type    = "A"

  alias {
    name                   = module.load_balancer.load_balancer_dns_name
    zone_id                = module.load_balancer.load_balancer_zone_id
    evaluate_target_health = true
  }
}


module "django-app" {
  create_listener    = false
  create_networking  = false
  memory             = 4096
  cpu                = 2048
  source             = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name       = "redbox-django-app"
  image_tag          = var.image_tag
  prefix             = "frontend"
  ecr_repository_uri = "${var.ecr_repository_uri}/redbox-django-app"
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
  container_port               = 8090
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  host                         = local.django_host
  ip_whitelist                 = var.external_ips
  environment_variables        = local.environment_variables
}


module "core_api" {
  memory             = 4096
  cpu                = 2048
  create_listener    = true
  create_networking  = true
  source             = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name       = "redbox-core-api"
  image_tag          = var.image_tag
  prefix             = "backend"
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
  host                         = local.api_host
  ip_whitelist                 = var.external_ips
  environment_variables        = local.environment_variables
}


module "worker" {
  create_networking  = false
  memory             = 4096
  cpu                = 2048
  source             = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name       = "redbox-worker"
  image_tag          = var.image_tag
  prefix             = "backend"
  ecr_repository_uri = "${var.ecr_repository_uri}/redbox-worker"
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
  host                         = local.api_host
  ip_whitelist                 = var.external_ips
  environment_variables        = local.environment_variables
}
