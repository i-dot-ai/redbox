module "rds" {
    source                  = "../../../i-ai-core-infrastructure//modules/postgres"
    db_name                 = "${var.project_name}-psql-rds-${var.env}"
    developer_ips           = []
    kms_secrets_arn         = data.terraform_remote_state.universal.outputs.kms_secrets_arn
    private_subnet_ids_list = data.terraform_remote_state.vpc.outputs.private_subnets
    project                 = var.project_name
    public_subnet_ids_list  = data.terraform_remote_state.vpc.outputs.public_subnets
    service_sg_ids          = [
        module.ingester.ecs_sg_id,
        module.core_api.ecs_sg_id,
        module.embedder.ecs_sg_id,
    ]
    state_bucket = var.state_bucket
    task_prefix  = var.project_name
    vpc_id       = data.terraform_remote_state.vpc.outputs
}