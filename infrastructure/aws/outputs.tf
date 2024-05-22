output "user_data_bucket_arn" {
    description = "Arn of the bucket used to store user documents"
    value       = aws_s3_bucket.user_data_bucket.arn
}

output "user_data_bucket_id" {
    description = "Id of the bucket used to store user documents"
    value       = aws_s3_bucket.user_data_bucket.id
}

output "user_data_bucket_name" {
    description = "The name of the bucket used to store user documents"
    value       = aws_s3_bucket.user_data_bucket.bucket
}

output "load_balancer_dns_name" {
    description = "DNS name of the alb"
    value       = module.load_balancer.load_balancer_dns_name
}

output "load_balancer_zone_id" {
    description = "Zone ID of the alb"
    value       = module.load_balancer.load_balancer_zone_id
}

output "ecs_cluster_id" {
    description = "The ID of the ECS cluster"
    value       = module.cluster.ecs_cluster_id
}

output "load_balancer_security_group_id" {
    description = "The ID of the load balancers security group"
    value       = module.load_balancer.load_balancer_security_group_id
}

output "alb_arn" {
    description = "The ARN of the load balancer"
    value       = module.load_balancer.alb_arn
}

output "core_api_ecs_sg_id" {
    description = "The security group ID of the core-api ecs"
    value       = module.core_api.ecs_sg_id
}

output "service_discovery_service_name" {
    description = "The name of the service-discovery service"
    value       = aws_service_discovery_service.service_discovery_service.name
}

output "private_dns_namespace_name" {
    description = "The name of the ecs private dns namespace"
    value       = aws_service_discovery_private_dns_namespace.private_dns_namespace.name
}