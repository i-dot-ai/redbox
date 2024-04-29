locals {
  repos = [
    "core-api",
    "db",
    "django-app",
    "worker",
    "redbox",
  ]
}

module "ecs" {
  source = "../../../../i-ai-core-infrastructure//modules/ecr"

  for_each              = { for repo in local.repos : repo => repo }
  project_name          = var.project_name
  container_name_suffix = each.value
}
