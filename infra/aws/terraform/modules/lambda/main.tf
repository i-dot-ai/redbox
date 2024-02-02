variable "function_name" {}
variable "runtime" {}
variable "handler" {}
variable "source_path" {}

resource "aws_lambda_function" "lambda_function" {
 function_name = var.function_name
 role         = aws_iam_role.iam_for_lambda.arn
 handler      = var.handler
 runtime      = var.runtime
 filename     = "${var.source_path}/lambda_package.zip"

 source_code_hash = filebase64sha256("${var.source_path}/lambda_package.zip")
}
