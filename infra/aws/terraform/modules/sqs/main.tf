variable "queue_name" {
 description = "The name of the SQS queue"
 type        = string
}

variable "max_message_size" {
 description = "The limit of how many bytes a message can contain before Amazon SQS rejects it"
 type        = number
 default     = 262144 # 256 KB
}

variable "message_retention_seconds" {
 description = "The length of time, in seconds, for which Amazon SQS retains a message"
 type        = number
 default     = 345600 # 4 days
}

variable "visibility_timeout_seconds" {
 description = "The length of time, in seconds, during which a message received from a queue will be invisible to other receiving components when they ask to receive messages"
 type        = number
 default     = 30
}

variable "delay_seconds" {
 description = "The time in seconds that the delivery of all messages in the queue will be delayed"
 type        = number
 default     = 0
}

variable "receive_wait_time_seconds" {
 description = "The duration (in seconds) for which a ReceiveMessage call will wait for a message to arrive in the queue before returning"
 type        = number
 default     = 0
}

resource "aws_sqs_queue" "sqs_queue" {
 name                        = var.queue_name
 delay_seconds               = var.delay_seconds
 max_message_size            = var.max_message_size
 message_retention_seconds   = var.message_retention_seconds
 receive_wait_time_seconds   = var.receive_wait_time_seconds
 visibility_timeout_seconds = var.visibility_timeout_seconds
}
