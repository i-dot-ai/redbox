output "db_instance_address" {
  value       = module.rds.db_instance_address
  description = "The address of the rds instance"
}

output "db_master_username" {
  value       = module.rds.rds_instance_username
  description = "The master username of the rds instance"
  sensitive   = true
}

output "db_master_password" {
  value       = module.rds.rds_instance_db_password
  description = "The master password of the rds instance"
  sensitive   = true
}
