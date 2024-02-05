data "aws_secretsmanager_secret_version" "env_secret" {
  secret_id = "queue-${var.environment}"
}