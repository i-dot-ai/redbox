module "opensearch" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  source          = "git@github.com:i-dot-ai/i-ai-core-infrastructure.git//modules/opensearch"
  environment     = var.env
  state_bucket    = var.state_bucket
  collection_name = "redbox-documents"
  region          = var.region
  type            = "VECTORSEARCH"
  account_id      = var.account_id
}