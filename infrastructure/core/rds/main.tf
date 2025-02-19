resource "aws_security_group" "rds" {
  # checkov:skip=CKV2_AWS_5: It's attached to the module, so this check isn't right
  name        = "${var.name}-postgres-db-sg"
  vpc_id      = var.vpc_id
  description = "Security group for rds"

  lifecycle {
    create_before_destroy = true
  }

}

resource "aws_security_group_rule" "service_to_db_ingress" {
  count                    = length(var.service_sg_ids)
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = var.service_sg_ids[count.index]
  description              = "Allow incoming requests to RDS from execution services"
}

resource "aws_security_group_rule" "developer_to_db_ingress" {
  for_each          = toset(var.securelist_ips)
  type              = "ingress"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  security_group_id = aws_security_group.rds.id
  cidr_blocks       = [each.value]

  description = "Allow incoming requests to RDS from developer IPs for development purposes. "
}

resource "aws_security_group_rule" "vpc_db_ingress" {
  type              = "ingress"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  security_group_id = aws_security_group.rds.id
  cidr_blocks       = var.vpc_source_ips
  description       = "Allow incoming requests to RDS from private IP addresses in VPC private subnet."
}


module "rds" {
  # Using v6.5.5 of the postgres terraform aws module
  source     = "git::https://github.com/terraform-aws-modules/terraform-aws-rds.git?ref=e64ce07404b30da55bc5c7400b1ecdaa5831c2a6"
  identifier = "${var.name}-db"
  # storage
  allocated_storage = 20
  storage_encrypted = true
  storage_type      = "gp2"

  backup_retention_period          = 35
  backup_window                    = "03:30-04:30"
  copy_tags_to_snapshot            = true
  final_snapshot_identifier_prefix = "${var.name}-final"
  skip_final_snapshot              = true


  deletion_protection         = true
  create_db_subnet_group      = true
  engine                      = "postgres"
  engine_version              = "16.3"
  family                      = "postgres16"
  instance_class              = var.instance_type
  major_engine_version        = 16
  multi_az                    = true
  db_name                     = var.db_name
  port                        = 5432
  publicly_accessible         = var.publicly_accessible
  manage_master_user_password = false
  password                    = random_password.db_master_pass.result
  username                    = var.username

  subnet_ids             = var.public_subnet_ids_list
  vpc_security_group_ids = [aws_security_group.rds.id]
}
