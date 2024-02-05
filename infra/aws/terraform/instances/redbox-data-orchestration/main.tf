module "ecs_cluster" {
  source       = "../../modules/ecs"
  cluster_name = "${var.project_name}-${var.environment}-cluster"
}

module "ecs_service" {
  source              = "../../modules/ecs_service"
  service_name        = "${var.project_name}-${var.environment}-service"
  cluster_id          = module.ecs_cluster.id
  task_definition_arn = module.ecs_task_definition.arn
  desired_count       = 1
}

module "ecr_repository" {
  source = "../../modules/ecr"
  ecr_name = "${var.project_name}-ecr"
}

module "ecs_task_definition" {
  source = "../../modules/ecs_container"
  family = "${var.project_name}-${var.environment}-task-def"
  cpu    = "1024"
  memory = "4096"
  containers = [
    {
      name      = "${var.project_name}-${var.environment}-embed"
      image     = "${module.ecr_repository.repository_url}:${var.embed_image_tag}"
      cpu       = 1024
      memory    = 4096
      essential = true
      port_mappings = [
        {
          name          = "django-application"
          containerPort = 8501
          protocol      = "tcp"
        }
      ]
      readonly_root_filesystem  = false
      enable_cloudwatch_logging = true
      secrets = [
        {
          name      = "DJANGO_SECRET_KEY",
          valueFrom = "${data.aws_secretsmanager_secret_version.env_secret.arn}:DJANGO_SECRET_KEY::",
        }
      ],
      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
      ]
    }
  ]
}

module "sqs" {
  source     = "../../modules/sqs"
  queue_name = "${var.project_name}-${var.environment}-sqs"
}

module "ecs_sqs_autoscaling" {
  source             = "../../modules/ecs_sqs_autoscaling"
  cluster_name       = module.ecs_cluster.name
  evaluation_periods = 1
  max_tasks          = 0
  min_tasks          = 0
  period             = 30
  queue_name         = module.sqs.name
  service_name       = module.ecs_service.name
  threshold          = 10
}
