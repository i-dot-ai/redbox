module "django-lambda" {
  for_each = {
    for index, command in var.django_command :
    command.task_name => command
  }
  source       = "../../../i-ai-core-infrastructure//modules/lambda"
  image_config = {
    command = ["venv/bin/django-admin", each.value.command]
  }
  package_type                   = "Image"
  image_uri                      = "${var.ecr_repository_uri}/${var.project_name}-django-app:${lower(var.env)}"
  function_name                  = "${local.name}-${each.value.task_name}-lambda"
  iam_role_name                  = "${local.name}-${each.value.task_name}-lambda-role"
  timeout                        = 600
  reserved_concurrent_executions = 1
  environment_variables          = merge(local.django_app_secrets, local.django_lambda_environment_variables)
  aws_security_group_ids         = [aws_security_group.django_lambda_security_group.id]
  subnet_ids                     = data.terraform_remote_state.vpc.outputs.private_subnets
  policies                       = [jsonencode(data.aws_iam_policy_document.lambda_policy.json)]
  schedule                       = each.value.schedule
  account_id                     = var.account_id
  retries                        = 0
  event_age                      = 60
}

resource "aws_security_group" "django_lambda_security_group" {
  vpc_id      = data.terraform_remote_state.vpc.outputs.vpc_id
  description = "${local.name} redbox lambda security group"
  name        = "${local.name}-redbox-lambda-sg"
  lifecycle {
    create_before_destroy = true
  }
}

data "aws_iam_policy_document" "lambda_policy" {
  # checkov:skip=CKV_AWS_108 - * in resources (to be fixed in following PR)
  # checkov:skip=CKV_AWS_109 - * in resources (to be fixed in following PR)
  # checkov:skip=CKV_AWS_356 - * in resources (to be fixed in following PR)
  # checkov:skip=CKV_AWS_111 - * in resources (to be fixed in following PR)
  statement {
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    effect    = "Allow"
    resources = [aws_s3_bucket.user_data.arn, "${aws_s3_bucket.user_data.arn}/*"]
  }
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    effect    = "Allow"
    resources = ["*"]
  }
}

resource "aws_security_group_rule" "lambda_to_rds_egress" {
  type                     = "egress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.rds.postgres_sg_id
  security_group_id        = aws_security_group.django_lambda_security_group.id
  description              = "Allow requests from the lambda to get to the RDS"
}

resource "aws_security_group_rule" "lambda_to_443_egress" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  ipv6_cidr_blocks  = ["::/0"]
  security_group_id = aws_security_group.django_lambda_security_group.id
}
