module "rds" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  # source = "../../../i-dot-ai-core-terraform-modules//modules/infrastructure/rds"  # For testing local changes
  source                  = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/rds?ref=v1.0.0-rds"
  name                    = local.name
  db_name                 = var.project_name
  domain_name             = var.domain_name
  state_bucket            = var.state_bucket
  securelist_ips          = toset(concat(var.developer_ips, var.internal_ips))
  kms_secrets_arn         = data.terraform_remote_state.platform.outputs.kms_key_arn
  private_subnet_ids_list = data.terraform_remote_state.vpc.outputs.private_subnets
  public_subnet_ids_list  = data.terraform_remote_state.vpc.outputs.public_subnets
  vpc_id                  = data.terraform_remote_state.vpc.outputs.vpc_id
  instance_type           = var.env != "prod" ? "db.t3.micro" : "db.t3.large"
  service_sg_ids          = [
    module.worker.ecs_sg_id,
  ]
  secret_tags         = { "platform:secret-purpose" = "general" }
  publicly_accessible = var.publicly_accessible
}
