module "lambda" {
  source           = "../../../i-ai-core-infrastructure//modules/lambda"
  file_path        = "${path.module}/delete_expired_files/lambda_function.zip"
  function_name    = "${local.name}-delete-expired-files"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  iam_role_name    = "${local.name}-cleanup-lambda-role"
  environment_variables = {
    FILE_EXPIRY_IN_SECONDS: 7776000
  }
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/delete_expired_files/lambda_function.py"
  output_path = "${path.module}/delete_expired_files/lambda_function.zip"
}
