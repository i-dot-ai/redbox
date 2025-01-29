module "cluster" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  # source = "../../../i-ai-core-infrastructure//modules/ecs_cluster"
  source = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecs-cluster?ref=v1.0.0-ecs-cluster"
  name   = local.name
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
  name        = "${local.name}-internal"
  description = "redbox private dns namespace"
  vpc         = data.terraform_remote_state.vpc.outputs.vpc_id
}


resource "aws_service_discovery_service" "lit_ssr_service_discovery_service" {
  name = "${local.name}-lit-ssr"

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

resource "aws_service_discovery_service" "litellm_service_discovery_service" {
  name = "${local.name}-litellm"

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

resource "aws_secretsmanager_secret" "django-app-secret" {
  name = "${local.name}-django-app-secret"
  tags = {
    "platform:secret-purpose" = "general"
  }
}


resource "aws_secretsmanager_secret_version" "django-app-json-secret" {
  secret_id     = aws_secretsmanager_secret.django-app-secret.id
  secret_string = jsonencode(local.django_app_secrets)
}


module "django-app" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  #source                    = "../../i-dot-ai-core-terraform-modules//modules/infrastructure/ecs" # For testing local changes
  source                     = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecs?ref=v1.0.0-ecs"
  memory                     = 4096
  cpu                        = 2048
  create_listener            = true
  create_networking          = true
  name                       = "${local.name}-django-app"
  image_tag                  = var.image_tag
  ecr_repository_uri         = "${var.ecr_repository_uri}/${var.project_name}-django-app"
  ecs_cluster_id             = module.cluster.ecs_cluster_id
  ecs_cluster_name           = module.cluster.ecs_cluster_name
  autoscaling_minimum_target = 1
  autoscaling_maximum_target = 10
  health_check = {
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
  environment_variables        = local.django_app_environment_variables
  secrets                      = local.reconstructed_django_secrets
  auto_scale_off_peak_times    = true
  wait_for_ready_state         = true
}




module "worker" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  #source                      = "../../i-dot-ai-core-terraform-modules//modules/infrastructure/ecs" # For testing local changes
  source                       = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecs?ref=v1.0.0-ecs"
  command                      = ["venv/bin/django-admin", "qcluster"]
  memory                       = 6144
  cpu                          = 2048
  create_listener              = false
  create_networking            = false
  name                         = "${local.name}-worker"
  image_tag                    = var.image_tag
  ecr_repository_uri           = "${var.ecr_repository_uri}/${var.project_name}-django-app"
  ecs_cluster_id               = module.cluster.ecs_cluster_id
  ecs_cluster_name             = module.cluster.ecs_cluster_name
  autoscaling_minimum_target   = 1
  autoscaling_maximum_target   = 1
  state_bucket                 = var.state_bucket
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  container_port               = 5000
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ip_whitelist                 = var.external_ips
  environment_variables        = local.django_app_environment_variables
  secrets                      = local.reconstructed_django_secrets
  http_healthcheck             = false
  ephemeral_storage            = 30
  auto_scale_off_peak_times    = true
  wait_for_ready_state         = true
}


module "lit-ssr" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  #source                      = "../../i-dot-ai-core-terraform-modules//modules/infrastructure/ecs" # For testing local changes
  source                       = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecs?ref=v1.0.0-ecs"
  service_discovery_service_arn = aws_service_discovery_service.lit_ssr_service_discovery_service.arn
  memory                       = 6144
  cpu                          = 2048
  create_listener              = false
  create_networking            = false
  name                         = "${local.name}-lit-ssr"
  image_tag                    = var.image_tag
  ecr_repository_uri           = "${var.ecr_repository_uri}/${var.project_name}-lit-ssr"
  ecs_cluster_id               = module.cluster.ecs_cluster_id
  ecs_cluster_name             = module.cluster.ecs_cluster_name
  autoscaling_minimum_target   = 1
  autoscaling_maximum_target   = 1
  state_bucket                 = var.state_bucket
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  container_port               = 3002
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ip_whitelist                 = var.external_ips
  health_check = {
    healthy_threshold   = 3
    unhealthy_threshold = 3
    accepted_response   = "200"
    path                = "/health"
    timeout             = 5
  }
  ephemeral_storage            = 21
  auto_scale_off_peak_times    = true
  wait_for_ready_state         = true
}

module "litellm" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  #source                       = "../../i-dot-ai-core-terraform-modules//modules/infrastructure/ecs" # For testing local changes
  source                        = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecs?ref=v1.0.0-ecs"
  service_discovery_service_arn = aws_service_discovery_service.litellm_service_discovery_service.arn
  memory                        = 4096
  cpu                           = 2048
  create_listener               = false
  create_networking             = false
  name                          = "${local.name}-litellm"
  image_tag                     = "ghcr.io/berriai/litellm:main-latest"
  ecr_repository_uri            = "${var.ecr_repository_uri}/${var.project_name}-litellm"
  ecs_cluster_id                = module.cluster.ecs_cluster_id
  ecs_cluster_name              = module.cluster.ecs_cluster_name
  autoscaling_minimum_target    = 1
  autoscaling_maximum_target    = 1
  environment_variables         = local.django_app_environment_variables
  health_check = {
    healthy_threshold   = 3
    unhealthy_threshold = 3
    accepted_response   = "200"
    path                = "/test"
    timeout             = 5
  }
  state_bucket                 = var.state_bucket
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  container_port               = 4000
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ephemeral_storage            = 30
  auto_scale_off_peak_times    = true
  wait_for_ready_state         = true
}


resource "aws_security_group_rule" "ecs_ingress_django_to_lit_ssr" {
  type                     = "ingress"
  description              = "Allow all traffic from the django-app to lit-ssr"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  source_security_group_id = module.django-app.ecs_sg_id
  security_group_id        = module.lit-ssr.ecs_sg_id
}

resource "aws_security_group_rule" "ecs_django_to_litellm" {
  type                     = "ingress"
  description              = "Allow all traffic from the django-app to litellm"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  source_security_group_id = module.django-app.ecs_sg_id
  security_group_id        = module.litellm.ecs_sg_id
}