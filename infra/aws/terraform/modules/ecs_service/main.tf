variable "service_name" {
 description = "The name of the ECS service"
 type        = string
}

variable "cluster_id" {
 description = "The id of the ECS cluster"
 type        = string
}

variable "task_definition_arn" {
 description = "The ARN of the ECS task definition"
 type        = string
}

variable "desired_count" {
 description = "The number of tasks to run in the ECS service"
 type        = number
}

output "id" {
 value = aws_ecs_service.this.id
}

output "arn" {
 value = aws_ecs_service.this.arn
}


resource "aws_ecs_service" "this" {
 name            = var.service_name
 cluster         = var.cluster_id
 task_definition = var.task_definition_arn
 desired_count   = var.desired_count

 // Other configurations...
}
