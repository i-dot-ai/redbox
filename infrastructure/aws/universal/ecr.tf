module "ecr" {
  source                = "../../../../i-ai-core-infrastructure//modules/ecr"
  project_name          = var.project_name
  container_name_suffix = null
}
