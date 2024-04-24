module "load_balancer" {
  source          = "../../../i-ai-core-infrastructure/modules/load_balancer"
  project         = var.project_name
  region          = var.region
  state_bucket    = var.state_bucket
  account_id      = var.account_id
  vpc_id          = data.terraform_remote_state.vpc.outputs.vpc_id
  public_subnets  = data.terraform_remote_state.vpc.outputs.public_subnets
  ip_whitelist    = concat(var.internal_ips, var.developer_ips, var.external_ips)
  env             = var.env
  certificate_arn = data.terraform_remote_state.universal.outputs.certificate_arn
}



module "waf" {
  source         = "../../i-ai-core-infrastructure/modules/waf"
  project        = var.project_name
  ip_set         = concat(var.internal_ips, var.developer_ips, var.external_ips)
  use_case       = var.use_case
  scope          = var.scope
  rules          = var.rules
  universal_tags = var.universal_tags
}

