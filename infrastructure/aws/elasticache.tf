module "elasticache" {
  source          = "../../../i-ai-core-infrastructure//modules/elasticache"
  name            = local.name
  vpc_id          = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets = data.terraform_remote_state.vpc.outputs.private_subnets
  security_group_ids = tomap(
    {
      "worker"   = module.worker.ecs_sg_id,
      "core_api" = module.core_api.ecs_sg_id,
    }
  )
}
