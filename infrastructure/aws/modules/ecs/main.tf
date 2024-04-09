variable "cluster_name" {
  description = "The name of the ECS cluster"
  type        = string
}

output "id" {
  value = aws_ecs_cluster.this.id
}

output "arn" {
  value = aws_ecs_cluster.this.arn
}

output "name" {
  value = aws_ecs_cluster.this.name
}


resource "aws_ecs_cluster" "this" {
  name = var.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  capacity_providers = ["FARGATE"]
}
