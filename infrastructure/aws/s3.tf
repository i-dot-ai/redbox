resource "aws_s3_bucket" "user_data_bucket" {
  bucket = "${var.project_name}-${terraform.workspace}-user-data"
}