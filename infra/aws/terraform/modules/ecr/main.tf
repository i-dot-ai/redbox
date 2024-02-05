variable "ecr_name" {
    description = "The name of the ECR repository"
    type        = string
}

output "id" {
    value = aws_ecr_repository.this.id
}

output "name" {
    value = aws_ecr_repository.this.name
}

output "repository_url" {
    value = aws_ecr_repository.this.repository_url
}

resource "aws_ecr_repository" "this" {
  name                 = var.ecr_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}