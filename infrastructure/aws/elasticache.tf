module "elasticache" {
  source = "../../../i-ai-core-infrastructure//modules/elasticache"

  project_name      = var.project_name
  prefix            = "backend"
  vpc_id            = data.terraform_remote_state.vpc.outputs.vpc_id
  private_subnets   = data.terraform_remote_state.vpc.outputs.private_subnets
  security_group_id = module.load_balancer.load_balancer_security_group_id
}
