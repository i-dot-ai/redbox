variable "family" {
  description = "The family of the ECS task definition"
  type        = string
}

variable "network_mode" {
  description = "The network mode of the ECS task definition"
  type        = string
  default     = "awsvpc"
}

variable "cpu" {
  description = "The CPU value of the ECS task definition"
  type        = string
}

variable "memory" {
  description = "The memory value of the ECS task definition"
  type        = string
}

variable "containers" {
  description = "A list of container definitions"
  type = list(object({
    name  = string
    image = string
  }))
}

output "id" {
  value = aws_ecs_task_definition.this.id
}

output "arn" {
  value = aws_ecs_task_definition.this.arn
}


resource "aws_ecs_task_definition" "this" {
  family                   = var.family
  network_mode             = var.network_mode
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory

  container_definitions = jsonencode(var.containers)
}
