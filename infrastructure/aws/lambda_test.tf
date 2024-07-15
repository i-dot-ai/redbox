#module "lambda-test" {
#  source           = "../../../i-ai-core-infrastructure//modules/lambda"
#  file_path        = data.archive_file.code.output_path
#  function_name    = "${local.name}-ell-test"
#  handler          = "lambda.main"
#  runtime          = "python3.12"
#  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
#  iam_role_name    = "${local.name}-test-lambda-role"
#  layers           = [aws_lambda_layer_version.layer.arn]
#  environment_variables = {
#    FILE_EXPIRY_IN_SECONDS: 7776000
#  }
#}
#
#data "archive_file" "code" {
#  type        = "zip"
#  source_dir  = "${path.module}/test_lambda/code"
#  output_path = "${path.module}/test_lambda/code.zip"
#}
#
#
#resource "aws_lambda_layer_version" "layer" {
#  layer_name          = "test-layer"
#  filename            = data.archive_file.layer.output_path
#  source_code_hash    = data.archive_file.layer.output_base64sha256
#  compatible_runtimes = ["python3.12"]
#}
#
#
#data "archive_file" "layer" {
#  type        = "zip"
#  source_dir  = "${path.module}/test_lambda/layer"
#  output_path = "${path.module}/test_lambda/layer.zip"
#  depends_on  = [null_resource.pip_install]
#}
#
#
#resource "null_resource" "pip_install" {
#  triggers = {
#    shell_hash = sha256(file("${path.module}/test_lambda/requirements.txt"))
#  }
#
#  provisioner "local-exec" {
#    command = "python3 -m pip install -r ./test_lambda/requirements.txt -t ${path.module}/test_lambda/layer/python"
#  }
#}

