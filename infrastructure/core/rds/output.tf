output "db_instance_address" {
  value       = module.rds.db_instance_address
  description = "Address for default postgres instance"
}

output "db_instance_name" {
  value       = module.rds.db_instance_name
  description = "Name of the default db"
}

output "postgres_sg_id" {
  value       = aws_security_group.rds.id
  description = "ID for the RDS security group"
}

output "rds_instance_endpoint" {
  value       = module.rds.db_instance_endpoint
  description = "Endpoint for default postgres instance"
  sensitive   = true
}

output "rds_instance_db_password" {
  value       = random_password.db_master_pass.result
  description = "Master RDS password for default postgres database"
  sensitive   = true
}

output "rds_instance_username" {
  value       = module.rds.db_instance_username
  description = "Master RDS username for core default postgres database"
}

output "rds_master_credentials_secret_name" {
  value       = aws_secretsmanager_secret.db_master_credentials.name
  description = "Name for the secret in secrets manager used to hold default postgres master credentials"
}
