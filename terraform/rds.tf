resource "aws_db_subnet_group" "main" {
  name       = "weather-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}


resource "aws_db_instance" "rds" {
  identifier              = "weather-db"
  engine                  = "postgres"
  engine_version          = "15" 
  instance_class          = "db.t4g.micro"  
  allocated_storage       = 20
  storage_type            = "gp3"
  storage_encrypted       = true
  # Auto-generate password and store in Secrets Manager
  username                       = var.db_user
  manage_master_user_password    = true

  db_name                 = var.db_name
  publicly_accessible     = false  
  skip_final_snapshot     = true  

  vpc_security_group_ids  = [aws_security_group.rds.id]
  db_subnet_group_name    = aws_db_subnet_group.main.name

  # Maintenance (best practice)
  backup_retention_period = 0
  auto_minor_version_upgrade = true

  tags = {
    Name    = "weather-db"
    Project = var.project
  }

  depends_on = [aws_security_group.rds]
}

resource "aws_security_group" "rds" {
  name        = "rds-weather-sg"
  description = "Allow inbound from Lambda only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id, aws_security_group.beanstalk_elb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "rds-weather-sg" }
}