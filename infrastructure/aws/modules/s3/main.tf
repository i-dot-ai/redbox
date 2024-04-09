variable "bucket_name" {}
variable "lambda_function_arn" {
  default = ""
}

resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name

  dynamic "notification_configuration" {
    for_each = var.lambda_function_arn != "" ? [1] : []
    content {
      lambda_function {
        lambda_function_arn = var.lambda_function_arn
        events              = ["s3:ObjectCreated:*"]
      }
    }
  }
}

resource "aws_s3_bucket_acl" "this" {
  depends_on = [aws_s3_bucket_ownership_controls.this]

  bucket = aws_s3_bucket.this.id
  acl    = "private"
}

resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}
