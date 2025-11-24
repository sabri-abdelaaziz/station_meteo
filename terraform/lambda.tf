resource "aws_iam_role" "lambda" {
  name = "weather-mqtt-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Allow Lambda to read DB password + MQTT certs
resource "aws_iam_role_policy" "lambda_secrets" {
  name = "weather-lambda-secrets"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
        Resource = [
          aws_db_instance.rds.master_user_secret[0].secret_arn,
          aws_secretsmanager_secret.mqtt_certs.arn
        ]
      }
    ]
  })
}

resource "aws_lambda_layer_version" "mqtt_deps" {
  layer_name          = "paho-p8000-boto3"
  description         = "Python layer with paho-mqtt, pg8000, and boto3"
  s3_bucket           = aws_s3_bucket.lambda_layers.id
  s3_key              = aws_s3_object.layer_zip.key
  compatible_runtimes = ["python3.12", "python3.11", "python3.10"]
  compatible_architectures = ["x86_64"]
  
  # This ensures the layer updates when the S3 object changes
  source_code_hash = filebase64sha256("${path.module}/mqtt_layer.zip")

  depends_on = [aws_s3_object.layer_zip]
}

resource "aws_lambda_function" "mqtt_subscriber" {
  filename         = "lambda_function.zip"
  function_name    = "WeatherMQTTSubscriber"
  role             = aws_iam_role.lambda.arn
  source_code_hash = filebase64sha256("lambda_function.zip")
  handler          = "subscriber.handler"
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 256
  layers           = [aws_lambda_layer_version.mqtt_deps.arn]

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids   = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      MQTT_HOST              = var.mqtt_broker_host
      MQTT_PORT              = var.mqtt_port
      MQTT_TOPIC             = var.mqtt_topic
      DB_HOST                = aws_db_instance.rds.address
      DB_PORT                = 5432
      DB_NAME                = var.db_name
      DB_USER                = var.db_user
      DB_PASSWORD_SECRET_ARN = aws_db_instance.rds.master_user_secret[0].secret_arn
      MQTT_SECRET_NAME       = aws_secretsmanager_secret.mqtt_certs.name
    }
  }
}

# MQTT TLS Certs
resource "aws_secretsmanager_secret" "mqtt_certs" {
  name = "mqtt/certs/weather"
}

resource "aws_secretsmanager_secret_version" "mqtt_certs" {
  secret_id     = aws_secretsmanager_secret.mqtt_certs.id
  secret_string = jsonencode({
    client_cert = file("certs/client.crt")
    client_key  = file("certs/client.key")
    ca_cert     = file("certs/ca.crt")
  })
}

# Outputs
output "layer_arn" {
  description = "ARN of the Lambda layer"
  value       = aws_lambda_layer_version.mqtt_deps.arn
}

output "layer_version_arn" {
  description = "Version ARN of the Lambda layer"
  value       = aws_lambda_layer_version.mqtt_deps.layer_arn
}

output "layer_version" {
  description = "Version number of the Lambda layer"
  value       = aws_lambda_layer_version.mqtt_deps.version
}

output "s3_bucket" {
  description = "S3 bucket containing the layer"
  value       = aws_s3_bucket.lambda_layers.bucket
}

output "s3_key" {
  description = "S3 key of the layer zip file"
  value       = aws_s3_object.layer_zip.key
}

# === Security Group for Lambda ===
resource "aws_security_group" "lambda" {
  name        = "${var.project}-lambda-sg"
  description = "Allow Lambda outbound to RDS and MQTT broker"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-lambda-sg" }
}
