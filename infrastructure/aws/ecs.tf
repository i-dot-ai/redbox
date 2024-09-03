module "cluster" {
  source = "../../../i-ai-core-infrastructure//modules/ecs_cluster"
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

resource "aws_service_discovery_service" "core_api_service_discovery_service" {
  name = "${local.name}-core-api"

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

resource "aws_service_discovery_service" "unstructured_service_discovery_service" {
  name = "${local.name}-unstructured"

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

resource "aws_secretsmanager_secret" "core-api-secret" {
  name = "${local.name}-core-api-secret"
  tags = {
    "platform:secret-purpose" = "general"
  }
}

resource "aws_secretsmanager_secret" "django-app-secret" {
  name = "${local.name}-django-app-secret"
  tags = {
    "platform:secret-purpose" = "general"
  }
}

resource "aws_secretsmanager_secret" "worker-secret" {
  name = "${local.name}-worker-secret"
  tags = {
    "platform:secret-purpose" = "general"
  }
}

resource "aws_secretsmanager_secret_version" "core-api-json-secret" {
  secret_id     = aws_secretsmanager_secret.core-api-secret.id
  secret_string = jsonencode(local.core_secrets)
}

resource "aws_secretsmanager_secret_version" "django-app-json-secret" {
  secret_id     = aws_secretsmanager_secret.django-app-secret.id
  secret_string = jsonencode(local.django_app_secrets)
}


module "django-app" {
  memory                     = 4096
  cpu                        = 2048
  create_listener            = true
  create_networking          = true
  source                     = "../../../i-ai-core-infrastructure//modules/ecs"
  name                       = "${local.name}-django-app"
  image_tag                  = var.image_tag
  ecr_repository_uri         = "${var.ecr_repository_uri}/${var.project_name}-django-app"
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
  environment_variables        = local.django_app_environment_variables
  secrets                      = local.reconstructed_django_secrets
  auto_scale_off_peak_times    = true
  wait_for_ready_state         = true
}

module "core_api" {
  service_discovery_service_arn = aws_service_discovery_service.core_api_service_discovery_service.arn
  memory                        = 4096
  cpu                           = 2048
  create_listener               = false
  create_networking             = false
  source                        = "../../../i-ai-core-infrastructure//modules/ecs"
  name                          = "${local.name}-core-api"
  image_tag                     = var.image_tag
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
  environment_variables        = local.core_api_environment_variables
  secrets                      = local.reconstructed_core_secrets
  ephemeral_storage            = 30
  auto_scale_off_peak_times    = true
  wait_for_ready_state         = true
}

module "unstructured" {
  service_discovery_service_arn = aws_service_discovery_service.unstructured_service_discovery_service.arn
  memory                        = 4096
  cpu                           = 2048
  create_listener               = false
  create_networking             = false
  source                        = "../../../i-ai-core-infrastructure//modules/ecs"
  name                          = "${local.name}-unstructured"
  image_tag                     = "latest"
  ecr_repository_uri            = "quay.io/unstructured-io/unstructured-api"
  ecs_cluster_id                = module.cluster.ecs_cluster_id
  ecs_cluster_name              = module.cluster.ecs_cluster_name
  autoscaling_minimum_target    = 1
  autoscaling_maximum_target    = 1
  health_check                  = {
    healthy_threshold   = 3
    unhealthy_threshold = 3
    accepted_response   = "200"
    path                = "/healthcheck"
    timeout             = 5
  }
  state_bucket                 = var.state_bucket
  vpc_id                       = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets              = data.terraform_remote_state.vpc.outputs.private_subnets
  container_port               = 8000
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  aws_lb_arn                   = module.load_balancer.alb_arn
  ephemeral_storage            = 30
  auto_scale_off_peak_times    = true
  wait_for_ready_state         = true
}


module "worker" {
  command                      = ["venv/bin/django-admin", "qcluster"]
  memory                       = 6144
  cpu                          = 2048
  create_listener              = false
  create_networking            = false
  source                       = "../../../i-ai-core-infrastructure//modules/ecs"
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


resource "aws_security_group_rule" "ecs_ingress_front_to_back" {
  type                     = "ingress"
  description              = "Allow all traffic from the django-app to the core-api"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  source_security_group_id = module.django-app.ecs_sg_id
  security_group_id        = module.core_api.ecs_sg_id
}


resource "aws_security_group_rule" "ecs_ingress_worker_to_unstructured" {
  type                     = "ingress"
  description              = "Allow all traffic from the worker to unstructured"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  source_security_group_id = module.worker.ecs_sg_id
  security_group_id        = module.unstructured.ecs_sg_id
}

resource "aws_security_group_rule" "allow_lambdas_ingress_to_django" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  source_security_group_id = aws_security_group.django_lambda_security_group.id
  security_group_id = module.django-app.ecs_sg_id
}

resource "aws_security_group_rule" "allow_lambdas_ingress_to_core" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  source_security_group_id = aws_security_group.django_lambda_security_group.id
  security_group_id = module.core_api.ecs_sg_id
}
