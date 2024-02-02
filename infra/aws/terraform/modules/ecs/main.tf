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


resource "aws_ecs_cluster" "this" {
 name = var.cluster_name
}
