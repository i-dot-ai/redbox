locals {
  record_prefix = terraform.workspace == "prod" ? var.project_name : "${var.project_name}-${terraform.workspace}"
  django_host   = "${local.record_prefix}.${var.domain_name}"

  environment_variables = {
    "ELASTIC__API_KEY" : var.elastic_api_key,
    "ELASTIC__CLOUD_ID" : var.cloud_id,
    "ELASTIC_ROOT_INDEX": "redbox-data-${terraform.workspace}",
    "OBJECT_STORE" : "s3",
    "BUCKET_NAME" : aws_s3_bucket.user_data_bucket.bucket,
    "EMBEDDING_MODEL" : "all-mpnet-base-v2",
    "EMBED_QUEUE_NAME" : "redbox-embedder-queue",
    "INGEST_QUEUE_NAME" : "redbox-ingester-queue",
    "REDIS_HOST" : module.elasticache.redis_address,
    "REDIS_PORT" : module.elasticache.redis_port,

    # django stuff
    "DJANGO_SECRET_KEY" : var.django_secret_key,
    "POSTGRES_USER" : module.rds.rds_instance_username,
    "POSTGRES_PASSWORD" : module.rds.rds_instance_db_password,
    "POSTGRES_DB" : module.rds.db_instance_name,
    "POSTGRES_HOST" : module.rds.db_instance_address,
    "CORE_API_HOST" : "${aws_service_discovery_service.service_discovery_service.name}.${aws_service_discovery_private_dns_namespace.private_dns_namespace.name}",
    "CORE_API_PORT" : 5002,
    "ENVIRONMENT" : upper(terraform.workspace),
    "DJANGO_SETTINGS_MODULE" : "redbox_app.settings",
    "DEBUG" : true,
    "AWS_REGION" : var.region,
    "FROM_EMAIL" : var.from_email,
    "OPENAI_API_VERSION": var.openai_api_version,
    "AZURE_OPENAI_MODEL": var.azure_openai_model,
    "AZURE_OPENAI_ENDPOINT": var.azure_openai_endpoint,
    "AZURE_OPENAI_API_KEY": var.azure_openai_api_key
    "GOVUK_NOTIFY_PLAIN_EMAIL_TEMPLATE_ID" : var.govuk_notify_plain_email_template_id
    "GOVUK_NOTIFY_API_KEY" : var.govuk_notify_api_key,
    "EMAIL_BACKEND_TYPE" : "GOVUKNOTIFY",
    "USE_STREAMING" : false,
    "DJANGO_LOG_LEVEL" : "DEBUG",
    "COMPRESSION_ENABLED" : true,
    "CONTACT_EMAIL": var.contact_email,
    "FILE_EXPIRY_IN_DAYS": 30,
    "MAX_SECURITY_CLASSIFICATION": "OFFICIAL_SENSITIVE",
    "WEBSOCKET_SCHEME": "wss"
  }
}


module "cluster" {
  source         = "../../../i-ai-core-infrastructure//modules/ecs_cluster"
  project_prefix = var.project_name
  name           = "${terraform.workspace}-${var.project_name}"
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

module "django-app" {
  memory                     = 4096
  cpu                        = 2048
  create_listener            = true
  create_networking          = true
  source                     = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name               = "django-app"
  image_tag                  = var.image_tag
  prefix                     = "redbox"
  ecr_repository_uri         = "${var.ecr_repository_uri}/redbox-django-app"
  ecs_cluster_id             = module.cluster.ecs_cluster_id
  ecs_cluster_name           = module.cluster.ecs_cluster_name
  autoscaling_minimum_target = 1
  autoscaling_maximum_target = 10
  health_check               = {
    healthy_threshold   = 3
    unhealthy_threshold = 3
    accepted_response   = "200"
    path                = "/health/"
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
  ecs_cluster_name              = module.cluster.ecs_cluster_name
  autoscaling_minimum_target    = 1
  autoscaling_maximum_target    = 10
  health_check                  = {
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
  memory                       = 6144
  cpu                          = 2048
  create_listener              = false
  create_networking            = false
  source                       = "../../../i-ai-core-infrastructure//modules/ecs"
  project_name                 = "worker"
  image_tag                    = var.image_tag
  prefix                       = "redbox"
  ecr_repository_uri           = "${var.ecr_repository_uri}/redbox-worker"
  ecs_cluster_id               = module.cluster.ecs_cluster_id
  ecs_cluster_name             = module.cluster.ecs_cluster_name
  autoscaling_minimum_target = 1
  autoscaling_maximum_target = 10
  state_bucket                 = var.state_bucket
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  container_port               = 5000
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ip_whitelist                 = var.external_ips
  environment_variables        = local.environment_variables
  http_healthcheck             = false
}


resource "aws_security_group_rule" "ecs_ingress_front_to_back" {
  type                     = "ingress"
  description              = "Allow all traffic from the django-app to the core-api"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  source_security_group_id = module.django-app.ecs_sg_id
  security_group_id        = module.core_api.ecs_sg_id
}
