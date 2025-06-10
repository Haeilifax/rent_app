locals {
  project_name = "RentApp"
  valid_stages = ["prod"]
}

terraform {

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
  }

  required_version = ">= 1.11.3"
}

provider "aws" {
  region = "us-east-1"
}

variable "stage" {
  # Go vote on https://github.com/hashicorp/terraform/issues/25283 for enum
  # values in Terraform
  type        = string
  description = "The deployment stage (such as prod) of this deployment"
  default     = "prod" # We don't have (or need) any stages besides prod right now

  validation {
    condition     = can(regex("(${join(")|(", local.valid_stages)})", var.stage))
    error_message = "Stage must be one of ${join(",", local.valid_stages)}"
  }
}

# Basis of lambda archiving and deploying taken from:
# https://callaway.dev/deploy-python-lambdas-with-terraform/
variable "lambda_root" {
  type        = string
  description = "The relative path to the source of the lambda"
  default     = "../lambda"
}

# Pull down the appropriate dependencies for our project
# We don't have support for different dependencies between stages -- if this
# becomes relevant, we'll need to figure that out
resource "terraform_data" "install_dependencies" {
  provisioner "local-exec" {
    command = "uv pip install --target ../build/layer/python -r ../pyproject.toml --python-platform aarch64-manylinux2014"
  }

  triggers_replace = {
    dependencies_versions = filemd5("../uv.lock")
  }
}

# Build our layer of dependencies for our lambda function
data "archive_file" "layer" {
  source_dir  = "../build/layer"
  output_path = "../build/layer.zip"
  type        = "zip"

  depends_on = [terraform_data.install_dependencies]
}

resource "aws_lambda_layer_version" "dependencies" {
  description = "Dependency layer for ${local.project_name}"
  layer_name  = "${local.project_name}-dependencies"
  filename    = data.archive_file.layer.output_path

  source_code_hash = data.archive_file.layer.output_md5
}

data "archive_file" "lambda_source" {
  # Build the archive file we'll upload for our lambda function
  source_dir  = var.lambda_root
  output_path = "../build/lambda.zip"
  type        = "zip"

  excludes = ["__pycache__"]
}

resource "aws_s3_bucket" "persistence_bucket" {
  bucket = "${lower(local.project_name)}-${lower(var.stage)}-persistence-bucket"
}

# The role policy definition below is based on:
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function#cloudwatch-logging-and-permissions
# See also the following AWS managed policy: AWSLambdaBasicExecutionRole
data "aws_iam_policy_document" "lambda_execution_role" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["arn:aws:logs:*:*:*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]

    resources = ["${aws_s3_bucket.persistence_bucket.arn}/*"]
  }
}

resource "aws_iam_policy" "lambda_execution_role" {
  name        = "${local.project_name}ExecutionPolicy"
  path        = "/"
  description = "The IAM role our Lambda will execute under"
  policy      = data.aws_iam_policy_document.lambda_execution_role.json
}

resource "aws_iam_role" "execution_role" {
  name = "${local.project_name}ExecutionRole"
  # assume_role_policy based on:
  # https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

data "aws_iam_policy" "basic_execution_role" {
  name = "AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "basic_execution_role" {
  role       = aws_iam_role.execution_role.name
  policy_arn = data.aws_iam_policy.basic_execution_role.arn
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.execution_role.name
  policy_arn = aws_iam_policy.lambda_execution_role.arn
}

resource "aws_lambda_function" "lambda" {
  function_name = "${local.project_name}-${var.stage}"
  # Use the role we created above
  role = aws_iam_role.execution_role.arn
  # Provide the zip file we created earlier
  filename = data.archive_file.lambda_source.output_path
  layers   = [aws_lambda_layer_version.dependencies.arn]

  handler       = "app.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  environment {
    variables = {
      STAGE = var.stage
    }
  }

  # Timeout needs to be higher than the default 3 seconds due to us fetching from
  # s3 on cold start
  timeout = 29

  # CONCURRENCY = 1 IS ESSENTIAL
  # We're overwriting our sqlite file in S3 with updates, so multiple instances
  # interacting with the same file has NO sensible conflict resolution
  reserved_concurrent_executions = 1

  source_code_hash = data.archive_file.lambda_source.output_md5
}

# Allow our function to be hit openly on the internet
resource "aws_lambda_function_url" "lambda_url" {
  function_name      = aws_lambda_function.lambda.function_name
  authorization_type = "NONE"
}
