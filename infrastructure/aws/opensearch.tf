module "opensearch" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  # source = "../../../i-dot-ai-core-terraform-modules//modules/infrastructure/opensearch"  # For testing local changes
  source = "git::https://github.com/i-dot-ai/i-dot-ai-core-terraform-modules.git//modules/infrastructure/opensearch?ref=v1.0.0-rds"
  environment = var.env
  state_bucket = var.state_bucket
  collection_name = "redbox-documents"
}