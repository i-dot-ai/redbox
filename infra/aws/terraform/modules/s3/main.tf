// s3_module/main.tf
variable "bucket_name" {}
variable "lambda_function_arn" {
  default = ""
}

resource "aws_s3_bucket" "bucket" {
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
