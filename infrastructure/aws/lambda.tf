#module "lambda" {
#  source           = "../../../i-ai-core-infrastructure//modules/lambda"
#  file_path        = "${path.module}/delete_expired_files/lambda_function.zip"
#  function_name    = "${local.name}-delete-expired-files"
#  handler          = "lambda_function.lambda_handler"
#  runtime          = "python3.12"
#  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
#  iam_role_name    = "${local.name}-cleanup-lambda-role"
#  environment_variables = {
#    FILE_EXPIRY_IN_SECONDS: 7776000
#  }
#
#  depends_on = [data.archive_file.lambda_zip]
#}
#
#data "archive_file" "lambda_zip" {
#  type        = "zip"
##  source_file = "${path.module}/delete_expired_files/lambda_function.py"
#  output_path = "${path.module}/delete_expired_files/lambda_function.zip"
#  source_dir = "${path.module}/delete_expired_files/"
##  source_file = "${path.module}/delete_expired_files/lambda_function.py"
#  excludes = ["${path.module}/delete_expired_files/lambda_function.zip"]
#}

module "lambda-cleanup" {
  source           = "../../../i-ai-core-infrastructure//modules/lambda"
  file_path        = data.archive_file.code.output_path
  function_name    = "${local.name}-cleanup-lambda"
  handler          = "lambda.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.code.output_base64sha256
  iam_role_name    = "${local.name}-redbox-cleanup-lambda-role"
  layers           = [aws_lambda_layer_version.layer.arn]
  environment_variables = {
    FILE_EXPIRY_IN_SECONDS: (local.django_app_environment_variables.FILE_EXPIRY_IN_DAYS * 24 * 60 * 60),
    POSTGRES_HOST: module.rds.db_instance_address,
    POSTGRES_DB: module.rds.db_instance_name,
    POSTGRES_USER: module.rds.rds_instance_username,
    POSTGRES_PASSWORD: module.rds.rds_instance_db_password,
    ELASTIC__CLOUD_ID: var.cloud_id,
    ELASTIC__API_KEY: var.elastic_api_key,
  }
}

data "archive_file" "code" {
  type        = "zip"
  source_dir  = "${path.module}/cleanup_lambda/code"
  output_path = "${path.module}/cleanup_lambda/code.zip"
}


resource "aws_lambda_layer_version" "layer" {
  layer_name          = "cleanup-layer"
  filename            = data.archive_file.layer.output_path
  source_code_hash    = data.archive_file.layer.output_base64sha256
  compatible_runtimes = ["python3.12"]
}


data "archive_file" "layer" {
  type        = "zip"
  source_dir  = "${path.module}/cleanup_lambda/layer"
  output_path = "${path.module}/cleanup_lambda/layer.zip"
  depends_on  = [null_resource.pip_install]
}


resource "null_resource" "pip_install" {
  triggers = {
    shell_hash = sha256(file("${path.module}/cleanup_lambda/requirements.txt"))
  }

  provisioner "local-exec" {
    command = "python3 -m pip install -r ./cleanup_lambda/requirements.txt -t ${path.module}/cleanup_lambda/layer/python"
  }
}

