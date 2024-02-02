variable "cluster_name" {
 description = "The name of the ECS cluster"
 type        = string
}

variable "service_name" {
 description = "The name of the ECS service"
 type        = string
}

variable "max_tasks" {
 description = "The maximum number of tasks that the ECS service should run"
 type        = number
}

variable "min_tasks" {
 description = "The minimum number of tasks that the ECS service should run"
 type        = number
}

variable "queue_name" {
 description = "The name of the SQS queue"
 type        = string
}

variable "evaluation_periods" {
 description = "The number of periods over which data is compared to the specified threshold"
 type        = number
}

variable "period" {
 description = "The period in seconds over which the specified statistic is applied"
 type        = number
}

variable "threshold" {
 description = "The value against which the specified statistic is compared"
 type        = number
}


resource "aws_appautoscaling_target" "ecs_target" {
 max_capacity       = var.max_tasks
 min_capacity       = var.min_tasks
 resource_id        = "service/${var.cluster_name}/${var.service_name}"
 scalable_dimension = "ecs:service:DesiredCount"
 service_namespace = "ecs"
}

resource "aws_cloudwatch_metric_alarm" "high_utilization" {
 comparison_operator = "GreaterThanOrEqualToThreshold"
 evaluation_periods = var.evaluation_periods
 metric_name         = "ApproximateNumberOfMessagesVisible"
 namespace           = "AWS/SQS"
 period              = var.period
 statistic           = "SampleCount"
 threshold           = var.threshold
 alarm_description   = "This metric checks if the number of messages in the queue exceeds the threshold."
 alarm_actions       = [aws_appautoscaling_policy.scale_up.arn]
  alarm_name = "${var.cluster_name}_${var.service_name}_${var.queue_name}_high_alarm"
 dimensions = {
   QueueName = var.queue_name
 }
}

resource "aws_cloudwatch_metric_alarm" "low_utilization" {
 comparison_operator = "LessThanOrEqualToThreshold"
 evaluation_periods = var.evaluation_periods
 metric_name         = "ApproximateNumberOfMessagesVisible"
 namespace           = "AWS/SQS"
 period              = var.period
 statistic           = "SampleCount"
 threshold           = var.threshold
 alarm_description   = "This metric checks if the number of messages in the queue is less than the threshold."
 alarm_actions       = [aws_appautoscaling_policy.scale_down.arn]
  alarm_name = "${var.cluster_name}_${var.service_name}_${var.queue_name}_low_alarm"
 dimensions = {
   QueueName = var.queue_name
 }
}

resource "aws_appautoscaling_policy" "scale_up" {
 name               = "scale-up"
 policy_type        = "StepScaling"
 resource_id        = aws_appautoscaling_target.ecs_target.resource_id
 scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
 service_namespace = aws_appautoscaling_target.ecs_target.service_namespace

 step_scaling_policy_configuration {
   adjustment_type         = "ChangeInCapacity"
   cooldown                = 300
   metric_aggregation_type = "Average"

   step_adjustment {
     metric_interval_lower_bound = 0
     scaling_adjustment          = 1
   }
 }
}

resource "aws_appautoscaling_policy" "scale_down" {
 name               = "scale-down"
 policy_type        = "StepScaling"
 resource_id        = aws_appautoscaling_target.ecs_target.resource_id
 scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
 service_namespace = aws_appautoscaling_target.ecs_target.service_namespace

 step_scaling_policy_configuration {
   adjustment_type         = "ChangeInCapacity"
   cooldown                = 300
   metric_aggregation_type = "Average"

   step_adjustment {
     metric_interval_upper_bound = 0
     scaling_adjustment          = -1
   }
 }
}
