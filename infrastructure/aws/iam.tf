data "aws_iam_policy_document" "ecs_exec_role_policy" {
  # checkov:skip=CKV_AWS_109:KMS policies can't be restricted
  # checkov:skip=CKV_AWS_111:KMS policies can't be restricted
  # checkov:skip=CKV_AWS_356:Allow for policies to not have resource limits

  statement {
    effect = "Allow"
    actions = [
      "bedrock:Invoke*",
      "bedrock:Get*",
      "bedrock:List*"
    ]
    resources = [
      "*"
    ]
  }

  # checkov:skip=CKV_AWS_111:Allow for write access without constraints
  # checkov:skip=CKV_AWS_356:Allow for policies to not have resource limits
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:AbortMultipartUpload",
      "s3:ListBucket",
      "s3:DeleteObject",
      "s3:GetObjectVersion",
      "s3:ListMultipartUploadParts",
    ]
    resources = [
      "arn:aws:s3:::${aws_s3_bucket.user_data.bucket}",
      "arn:aws:s3:::${aws_s3_bucket.user_data.bucket}/*",

    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      aws_secretsmanager_secret.django-app-secret.arn,
      "${aws_secretsmanager_secret.django-app-secret.arn}:*"
    ]
  }
}

resource "aws_iam_policy" "redbox_policy" {
  name        = "${local.name}-policy"
  description = "Allow application instance to log"
  policy      = data.aws_iam_policy_document.ecs_exec_role_policy.json
}

resource "aws_iam_role_policy_attachment" "redbox_role_policy" {
  for_each = tomap(
    {
      "worker" = module.worker.ecs_task_execution_exec_role_name,
      "django" = module.django-app.ecs_task_execution_exec_role_name,
    }
  )
  role       = each.value
  policy_arn = aws_iam_policy.redbox_policy.arn
}

resource "aws_iam_role_policy" "github-runner-policy" {
  name   = "${local.name}-github-runner-policy"
  role   = data.terraform_remote_state.platform.outputs.github_runner_execution_role_name
  policy = data.aws_iam_policy_document.github-runner.json
}

data "aws_iam_policy_document" "github-runner" {
  ### Allow access to redbox specific s3 buckets
  statement {
    effect  = "Allow"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.user_data.arn,
      "${aws_s3_bucket.user_data.arn}/*",
    ]
  }
}
