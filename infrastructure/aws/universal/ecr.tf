locals {
  repos = [
    "django-app",
  ]
}

module "ecr" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  # source = "../../../i-ai-core-infrastructure//modules/ecr"
  source = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/ecr?ref=v1.0.0-ecr"
  for_each = { for repo in local.repos : repo => repo }
  name     = "${var.project_name}-${each.value}"
}
