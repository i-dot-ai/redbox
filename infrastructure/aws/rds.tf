module "rds" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  # source = "../../../i-dot-ai-core-terraform-modules//modules/infrastructure/rds"  # For testing local changes
  source                  = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/rds?ref=v1.1.0-rds"
  engine                  = "postgres"
  engine_family           = "postgres16"
  engine_version          = "16.4"
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

module "rds-aurora" {
  #   source = "../../i-dot-ai-core-terraform-modules//modules/infrastructure/rds"  # For testing local changes
  source                 = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/rds?ref=v3.4.1-rds"
  db_name                = replace(var.project_name, "-", "_")
  kms_secrets_arn        = data.terraform_remote_state.platform.outputs.kms_key_arn
  name                   = local.name
  public_subnet_ids_list = data.terraform_remote_state.vpc.outputs.public_subnets
  securelist_ips = toset(var.ip_whitelist)
  service_sg_ids = [
    module.django-app.ecs_sg_id,
    module.worker.ecs_sg_id
  ]
  vpc_id                 = data.terraform_remote_state.vpc.outputs.vpc_id
  engine                 = "aurora-postgresql"
  engine_version         = "16.4"  # Could try this with newest 17.4 version, not sure if 16 -> 17 migration will work
  family                 = null
  engine_mode            = "provisioned"
  aurora_min_scaling     = 0.5
  aurora_max_scaling     = 1
  aurora_instance_count  = 1
  deletion_protection    = var.env == "dev" ? false : true
}
