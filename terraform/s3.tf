resource "random_id" "bucket" {
  byte_length = 6
}

resource "aws_s3_bucket" "static" {
  bucket = lower("weather-static-${random_id.bucket.hex}")

  tags = {
    Name    = "Weather Station Static and App"
    Project = var.project
    Environment = "production"
  }
}

resource "aws_s3_bucket_versioning" "static" {
  bucket = aws_s3_bucket.static.id
  versioning_configuration {
    status = "Enabled"
  }
}

# BLOCK ALL PUBLIC ACCESS
resource "aws_s3_bucket_public_access_block" "static" {
  bucket                  = aws_s3_bucket.static.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "static" {
  bucket = aws_s3_bucket.static.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# App ZIP upload
resource "aws_s3_object" "app_zip" {
  bucket = aws_s3_bucket.static.id
  key    = "django-app/v1-${formatdate("YYYYMMDD-hhmm", timestamp())}.zip"
  source = "app.zip"
  etag   = filemd5("app.zip")
}

# Create S3 bucket for Lambda layers
resource "aws_s3_bucket" "lambda_layers" {
  bucket = "paho-psycopg2-boto3"

  tags = {
    Name        = "Lambda Layers"
    Environment = "Production"
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "lambda_layers" {
  bucket = aws_s3_bucket.lambda_layers.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Upload the layer zip file to S3
resource "aws_s3_object" "layer_zip" {
  bucket = aws_s3_bucket.lambda_layers.id
  key    = "layers/mqtt_layer.zip"
  source = "${path.module}/mqtt_layer.zip"
  
  # This ensures the layer updates when the zip file changes
  etag = filemd5("${path.module}/mqtt_layer.zip")

  tags = {
    Name = "MQTT Layer Package"
  }
}
