resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/WeatherMQTTSubscriber"
  retention_in_days = 30
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "Lambda-MQTT-Errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.mqtt_subscriber.function_name
  }
}

resource "aws_sns_topic" "alerts" {
  name = "WeatherStationAlerts"
}

resource "aws_cloudwatch_event_rule" "every_5_minutes" {
  name        = "weather-mqtt-every-5-minutes"
  description = "Run Lambda every 5 minutes to read real MQTT broker"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.every_5_minutes.name
  arn       = aws_lambda_function.mqtt_subscriber.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mqtt_subscriber.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_5_minutes.arn
}