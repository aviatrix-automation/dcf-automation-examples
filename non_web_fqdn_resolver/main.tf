provider "aws" {
  region = "us-east-2"
}

locals {
  lambda_function_name = "avx_dcf_${var.resource_name}"
}

# local-exec provisioner to create the lambda_package.zip
resource "null_resource" "create_lambda_package" {
  triggers = {
    always_run = "${timestamp()}"
  }

  provisioner "local-exec" {
    command = "./lambda_function/create_lambda_archive.sh"
  }
}

# Create the IAM role for the Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "avx_dcf_${var.resource_name}_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Create a Lambda Layer with lambda_layer_dig
resource "aws_lambda_layer_version" "lambda_layer_dig" {
  layer_name = "avx_lambda_layer_dig"
  filename   = "${path.module}/lambda_layer_dig/dig-layer.zip"
  compatible_runtimes = ["python3.10","python3.11","python3.12"]
}

# Create a Lambda function with a CloudWatch trigger every 5 minutes
resource "aws_lambda_function" "fqdn_ip" {
  function_name = local.lambda_function_name
  handler       = "function.handler"
  runtime       = "python3.10"
  role          = aws_iam_role.lambda_role.arn
  source_code_hash = filebase64sha256("${path.module}/lambda_function/lambda_package.zip")
  timeout = var.timeout

  filename = "${path.module}/lambda_function/lambda_package.zip"

  layers = [ aws_lambda_layer_version.lambda_layer_dig.arn ]

  environment {
    variables = {
      LOG_LEVEL = "INFO"
      AVIATRIX_CONTROLLER_IP = var.controller_ip
      AVIATRIX_USERNAME = var.controller_user
      AVIATRIX_PASSWORD = var.controller_password
    }
  }

  depends_on = [ null_resource.create_lambda_package ]

  lifecycle {
    replace_triggered_by = [ null_resource.create_lambda_package ]
  }
}

# Create CloudWatch Event Rule to trigger lambda function every 5 minutes
resource "aws_cloudwatch_event_rule" "default" {
    name = "avx_dcf_${var.resource_name}"
    description = "Fires every ${var.frequency_minutes} minutes"
     schedule_expression = "rate(${var.frequency_minutes} minutes)"
}

resource "aws_cloudwatch_event_target" "default" {
    rule = aws_cloudwatch_event_rule.default.name
    target_id = "timed-trigger"
    arn = aws_lambda_function.fqdn_ip.arn
}

resource "aws_lambda_permission" "default" {
    statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = aws_lambda_function.fqdn_ip.function_name
    principal = "events.amazonaws.com"
    source_arn = aws_cloudwatch_event_rule.default.arn
}
