module "load_balancer" {
  source          = "../../../i-ai-core-infrastructure/modules/load_balancer"
  name            = local.name
  account_id      = var.account_id
  vpc_id          = data.terraform_remote_state.vpc.outputs.vpc_id
  public_subnets  = data.terraform_remote_state.vpc.outputs.public_subnets
  ip_whitelist    = concat(var.internal_ips, var.developer_ips, var.external_ips)
  certificate_arn = data.terraform_remote_state.universal.outputs.certificate_arn
  web_acl_arn     = module.waf.web_acl_arn
}



module "waf" {
  source         = "../../../i-ai-core-infrastructure/modules/waf"
  name           = local.name
  ip_set         = concat(var.internal_ips, var.developer_ips, var.external_ips)
  scope          = var.scope
  rules          = var.rules
  universal_tags = var.universal_tags
}
