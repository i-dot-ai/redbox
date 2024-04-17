locals {
  host = terraform.workspace == "prod" ? "${var.project_name}.ai.cabinetoffice.gov.uk" : "${var.project_name}-${terraform.workspace}.ai.cabinetoffice.gov.uk"
  prefix = "backend"
  bucket_name = "redbox-${terraform.workspace}"
}

module "cluster" {
  source         = "../../../i-ai-core-infrastructure//modules/ecs_cluster"
  project_prefix = local.prefix
  name = "redbox"
}

resource "aws_route53_record" "type-a-record" {
  zone_id = var.hosted_zone_id
  name    = local.host
  type    = "A"

  alias {
    name                   = data.terraform_remote_state.platform.outputs.dns_name["default"]
    zone_id                = data.terraform_remote_state.platform.outputs.zone_id["default"]
    evaluate_target_health = true
  }
}

module "core-api" {
  source             = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name       = var.project_name
  image_tag          = "09e2cf755630d3e785afec10daacdd86e4d33656"
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
  load_balancer_security_group = data.terraform_remote_state.platform.outputs.load_balancer_security_group_id["default"]
  aws_lb_arn                   = data.terraform_remote_state.platform.outputs.load_balancer_arn["default"]
  host                         = local.host
  environment_variables = {
    "ELASTIC__API_KEY": var.elastic_api_key,
    "ELASTIC__CLOUD_ID": var.cloud_id,
    "OBJECT_STORE": "s3",
    "BUCKET_NAME": local.bucket_name,
    "EMBEDDING_MODEL": "all-mpnet-base-v2",
    "EMBED_QUEUE_NAME": "redbox-embedder-queue",
    "INGEST_QUEUE_NAME": "redbox-ingester-queue",
    "REDIS_HOST": module.elasticache.redis_address,
    "REDIS_PORT": module.elasticache.redis_port,
    "DJANGO_SECRET_KEY": var.django_secret_key,
    "POSTGRES_PASSWORD": var.postgres_password
  }
}
