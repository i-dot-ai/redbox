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

output "name" {
  value = aws_ecs_service.this.name
}

resource "aws_ecs_service" "this" {
  name                               = var.service_name
  cluster                            = var.cluster_id
  task_definition                    = var.task_definition_arn
  desired_count                      = var.desired_count
  deployment_minimum_healthy_percent = 66
  deployment_maximum_percent         = 600
  launch_type                        = "FARGATE"
  # load_balancer {
  #  target_group_arn = ""
  #  container_name = ""
  #  container_port = 0
  # }
}
