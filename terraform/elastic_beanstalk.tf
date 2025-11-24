# IAM
resource "aws_iam_role" "beanstalk_ec2" {
  name = "weather-beanstalk-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}
resource "aws_iam_policy" "eb_secrets_access" {
  name        = "EBSecretsAccess"
  description = "Allow EB EC2 instances to read database secrets"
  policy      = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["secretsmanager:GetSecretValue"],
        Resource = [
          aws_secretsmanager_secret.django_secret.arn,
          aws_db_instance.rds.master_user_secret[0].secret_arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eb_secrets_policy" {
  role       = aws_iam_role.beanstalk_ec2.name
  policy_arn = aws_iam_policy.eb_secrets_access.arn
}

# Allow EB EC2 to access RDS
resource "aws_security_group_rule" "eb_to_rds" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = element(aws_db_instance.rds.vpc_security_group_ids, 0)
  source_security_group_id = aws_security_group.beanstalk_ec2.id
  description              = "Allow EB EC2 to connect to RDS"
}


resource "aws_iam_role_policy_attachment" "web_tier" {
  role       = aws_iam_role.beanstalk_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier"
}

resource "aws_iam_role_policy_attachment" "multicontainer" {
  role       = aws_iam_role.beanstalk_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker"
}

resource "aws_iam_instance_profile" "beanstalk" {
  name = "weather-beanstalk-profile"
  role = aws_iam_role.beanstalk_ec2.name
}

# Application & Version
resource "aws_elastic_beanstalk_application" "django" {
  name = "weather-django-app"
}

resource "aws_elastic_beanstalk_application_version" "current" {
  name        = "v1"
  application = aws_elastic_beanstalk_application.django.name
  bucket      = aws_s3_bucket.static.id
  key         = aws_s3_object.app_zip.key
}

# Environment
data "aws_elastic_beanstalk_solution_stack" "python" {
  most_recent = true
  name_regex   = "64bit Amazon Linux 2023.*running Python 3\\.11"
}

resource "aws_elastic_beanstalk_environment" "django_env" {
  name                = "weather-django-prod"
  application         = aws_elastic_beanstalk_application.django.name
  solution_stack_name = data.aws_elastic_beanstalk_solution_stack.python.name
  version_label       = aws_elastic_beanstalk_application_version.current.name

  setting { 
    namespace = "aws:ec2:vpc"            
    name = "VPCId"          
    value = aws_vpc.main.id 
  }
  setting { 
  namespace = "aws:ec2:vpc"            
  name = "Subnets"        
  value = join(",", aws_subnet.public[*].id) 
  }
  setting { 
    namespace = "aws:ec2:vpc"            
    name = "ELBSubnets"     
    value = join(",", aws_subnet.public[*].id) 
    }
  setting { 
    namespace = "aws:autoscaling:launchconfiguration" 
    name = "IamInstanceProfile" 
    value = aws_iam_instance_profile.beanstalk.name 
    }
  setting { 
    namespace = "aws:autoscaling:launchconfiguration" 
    name = "InstanceType"       
    value = "t3.micro" 
    }
  setting { 
    namespace = "aws:autoscaling:launchconfiguration" 
    name = "SecurityGroups"     
    value = aws_security_group.beanstalk_ec2.id 
    }
  setting { 
    namespace = "aws:elbv2:loadbalancer" 
    name = "SecurityGroups" 
    value = aws_security_group.beanstalk_elb.id 
    }

  setting { 
    namespace = "aws:elasticbeanstalk:application:environment"
    name = "SECRET_KEY_ARN" 
    value = aws_secretsmanager_secret.django_secret.arn 
    }
  setting { 
    namespace = "aws:elasticbeanstalk:application:environment" 
    name = "DB_PASSWORD_SECRET_ARN" 
    value = aws_db_instance.rds.master_user_secret[0].secret_arn
    }
  setting { 
  namespace = "aws:elasticbeanstalk:application:environment" 
  name      = "DB_NAME" 
  value     = var.db_name
}

  setting { 
    namespace = "aws:elasticbeanstalk:application:environment" 
    name      = "DB_USER" 
    value     = var.db_user
  }

  setting { 
    namespace = "aws:elasticbeanstalk:application:environment" 
    name      = "DB_HOST" 
    value     = aws_db_instance.rds.endpoint
  }

  setting { 
    namespace = "aws:elasticbeanstalk:application:environment" 
    name      = "DB_PORT" 
    value     = "5432"
  }
  setting { 
    namespace = "aws:elasticbeanstalk:application:environment" 
    name = "DATABASE_URL" 
    value = "postgresql://${var.db_user}@${aws_db_instance.rds.endpoint}/${var.db_name}" 
    }
  setting { 
    namespace = "aws:elasticbeanstalk:application:environment" 
    name = "S3_BUCKET_NAME" 
    value = aws_s3_bucket.static.id 
    }
  setting { 
    namespace = "aws:elasticbeanstalk:application:environment" 
    name = "AWS_REGION" 
    value = var.aws_region 
    }
  setting { 
    namespace = "aws:elasticbeanstalk:application:environment" 
    name = "DJANGO_SETTINGS_MODULE" 
    value = "config.settings.production" 
    }
  setting { 
    namespace = "aws:elasticbeanstalk:application:environment" 
    name = "DEBUG" 
    value = "False" 
    }

  depends_on = [aws_db_instance.rds]
}

# Security Groups
resource "aws_security_group" "beanstalk_elb" {
  name        = "weather-eb-elb-sg"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "beanstalk_ec2" {
  name        = "weather-eb-ec2-sg"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.beanstalk_elb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Django SECRET_KEY in Secrets Manager
resource "random_password" "django_secret" {
  length  = 50
  special = true
}

resource "aws_secretsmanager_secret" "django_secret" {
  name = "django/secret-key"
}

resource "aws_secretsmanager_secret_version" "django_secret" {
  secret_id     = aws_secretsmanager_secret.django_secret.id
  secret_string = random_password.django_secret.result
}