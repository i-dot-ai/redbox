locals {
  repos = [
    "core-api",
    "django-app",
    "worker",
  ]
}

module "ecr" {
  source   = "../../../../i-ai-core-infrastructure//modules/ecr"
  for_each = { for repo in local.repos : repo => repo }
  name     = "${var.project_name}-${each.value}"
}
