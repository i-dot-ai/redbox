locals {
  host = terraform.workspace == "prod" ? "${var.project_name}.ai.cabinetoffice.gov.uk" : "${var.project_name}-${terraform.workspace}.ai.cabinetoffice.gov.uk"
  prefix = "backend"
}

module "cluster" {
  source         = "../../../i-ai-core-infrastructure//modules/ecs_cluster"
  project_prefix = local.prefix
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
  image_tag          = var.image_tag
  prefix             = local.prefix
  ecr_repository_uri = "${var.ecr_repository_uri}/redbox-core-api"
  ecs_cluster_id     = module.cluster.ecs_cluster_id
  health_check = {
    healthy_threshold   = 3
    unhealthy_threshold = 3
    accepted_response   = "200"
    path                = "/"
    timeout             = 6
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
    "BUCKET_NAME": "redbox",
    "EMBEDDING_MODEL": "all-mpnet-base-v2",
    "EMBED_QUEUE_NAME": "redbox-embedder-queue",
    "INGEST_QUEUE_NAME": "redbox-ingester-queue",
    "REDIS_HOST": "redis",
    "REDIS_PORT": "6379",
    "DJANGO_SECRET_KEY": var.django_secret_key,
    "PSOTGRES_PASSWORD": var.postgres_password
  }
}

