resource "aws_s3_bucket" "user_data" {
  bucket = local.name
}
