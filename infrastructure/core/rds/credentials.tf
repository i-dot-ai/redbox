resource "random_password" "db_master_pass" {
  length           = 40
  special          = var.password_use_special
  min_special      = var.password_min_special
  override_special = var.password_override_special
  keepers = var.password_keeper
}

resource "aws_secretsmanager_secret" "db_master_credentials" {
  # checkov:skip=CKV2_AWS_57:Disable need for automatic rotation
  name        = "${var.name}-db-master-credentials"
  description = "Master credentials to the ${var.name} postgres database"
  kms_key_id  = var.kms_secrets_arn
  tags        = var.secret_tags
}

resource "aws_secretsmanager_secret_version" "db_master_credentials" {
  secret_id = aws_secretsmanager_secret.db_master_credentials.id
  secret_string = jsonencode({
    endpoint = module.rds.db_instance_endpoint,
    username = var.username,
    password = random_password.db_master_pass.result
  })

}
