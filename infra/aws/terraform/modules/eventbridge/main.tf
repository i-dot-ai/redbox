variable "rule_name" {}
variable "schedule_expression" {}
variable "lambda_function_name" {}

resource "aws_cloudwatch_event_rule" "event_rule" {
 name              = var.rule_name
 schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "event_target" {
 rule    = aws_cloudwatch_event_rule.event_rule.name
 target_id = var.lambda_function_name
 arn     = aws_lambda_function.lambda_function.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
 statement_id = "AllowExecutionFromCloudWatch"
 action      = "lambda:InvokeFunction"
 function_name = aws_lambda_function.lambda_function.function_name
 principal   = "events.amazonaws.com"
 source_arn  = aws_cloudwatch_event_rule.event_rule.arn
}
