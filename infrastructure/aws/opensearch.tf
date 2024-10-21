
module "opensearch" {
  # checkov:skip=CKV_TF_1: We're using semantic versions instead of commit hash
  # source = "../../../i-dot-ai-core-terraform-modules//modules/infrastructure/rds"  # For testing local changes
  source                  = "git@github.com:i-dot-ai/i-ai-core-infrastructure.git///modules/opensearch"
  account_id = var.account_id
  collection_name = "${var.team_name}-${terraform.workspace}-${var.project_name}-collection"
  type = "SEARCH"
  environment = var.env
  region = var.region
  state_bucket = var.state_bucket
}
