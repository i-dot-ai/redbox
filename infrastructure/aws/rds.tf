locals {
  dev_flag = var.env != "prod" ? true : false
}

module "rds" {
  source                  = "../../../i-ai-core-infrastructure//modules/postgres"
  project                 = "i-dot-ai"
  db_name                 = var.project_name
  task_prefix             = var.project_name
  domain_name             = var.domain_name
  state_bucket            = var.state_bucket
  developer_ips           = var.developer_ips
  kms_secrets_arn         = data.terraform_remote_state.platform.outputs.kms_key_arn
  private_subnet_ids_list = data.terraform_remote_state.vpc.outputs.private_subnets
  public_subnet_ids_list  = data.terraform_remote_state.vpc.outputs.public_subnets
  vpc_id                  = data.terraform_remote_state.vpc.outputs.vpc_id
  instance_type           = "db.t3.large"
  service_sg_ids = [
    module.ingester.ecs_sg_id,
    module.core_api.ecs_sg_id,
    module.embedder.ecs_sg_id,
  ]
  dev_instance     = local.dev_flag
  prod_maintenance = true
}
