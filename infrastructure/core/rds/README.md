<!-- BEGIN_TF_DOCS -->
## Requirements

No requirements.

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | n/a |
| <a name="provider_random"></a> [random](#provider\_random) | n/a |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_rds"></a> [rds](#module\_rds) | git::https://github.com/terraform-aws-modules/terraform-aws-rds.git | e64ce07404b30da55bc5c7400b1ecdaa5831c2a6 |

## Resources

| Name | Type |
|------|------|
| [aws_secretsmanager_secret.db_master_credentials](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret) | resource |
| [aws_secretsmanager_secret_version.db_master_credentials](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret_version) | resource |
| [aws_security_group.rds](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group) | resource |
| [aws_security_group_rule.developer_to_db_ingress](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group_rule) | resource |
| [aws_security_group_rule.service_to_db_ingress](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group_rule) | resource |
| [aws_security_group_rule.vpc_db_ingress](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group_rule) | resource |
| [random_password.db_master_pass](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/password) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_db_name"></a> [db\_name](#input\_db\_name) | Name for the default database attached to the RDS instance | `string` | n/a | yes |
| <a name="input_domain_name"></a> [domain\_name](#input\_domain\_name) | Domain name for Database e.g. <organisation>.getrapid.link. | `string` | n/a | yes |
| <a name="input_instance_type"></a> [instance\_type](#input\_instance\_type) | Instance type name for RDS | `string` | `"db.t3.micro"` | no |
| <a name="input_kms_secrets_arn"></a> [kms\_secrets\_arn](#input\_kms\_secrets\_arn) | ARN of KMS key for secret encryption. | `string` | n/a | yes |
| <a name="input_name"></a> [name](#input\_name) | The name that will be used as a prefix and to identify resources | `string` | n/a | yes |
| <a name="input_private_subnet_ids_list"></a> [private\_subnet\_ids\_list](#input\_private\_subnet\_ids\_list) | Private Subnet IDs for resource allocation. | `list(string)` | n/a | yes |
| <a name="input_public_subnet_ids_list"></a> [public\_subnet\_ids\_list](#input\_public\_subnet\_ids\_list) | Public Subnet IDs for resource allocation. | `list(string)` | n/a | yes |
| <a name="input_publicly_accessible"></a> [publicly\_accessible](#input\_publicly\_accessible) | A flag to indicate if the database should be publicly accessible or not | `bool` | `false` | no |
| <a name="input_secret_tags"></a> [secret\_tags](#input\_secret\_tags) | Tags to apply to the secrets | `map(string)` | `{}` | no |
| <a name="input_securelist_ips"></a> [securelist\_ips](#input\_securelist\_ips) | An IP securelist for Database access | `list(string)` | `[]` | no |
| <a name="input_service_sg_ids"></a> [service\_sg\_ids](#input\_service\_sg\_ids) | List of source security group IDs | `list(string)` | n/a | yes |
| <a name="input_state_bucket"></a> [state\_bucket](#input\_state\_bucket) | Name of the S3 bucket to use for terraform state | `string` | n/a | yes |
| <a name="input_username"></a> [username](#input\_username) | Username for the default database attached to the RDS instance | `string` | `"postgres"` | no |
| <a name="input_vpc_id"></a> [vpc\_id](#input\_vpc\_id) | VPC ID for resources to be assigned to. | `string` | n/a | yes |
| <a name="input_vpc_source_ips"></a> [vpc\_source\_ips](#input\_vpc\_source\_ips) | A list of the the private CIDR blocks that should be allowed access to the db. | `list(string)` | <pre>[<br>  "10.0.0.0/16",<br>  "10.73.0.0/16",<br>  "10.105.0.0/16"<br>]</pre> | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_db_instance_address"></a> [db\_instance\_address](#output\_db\_instance\_address) | Address for default postgres instance |
| <a name="output_db_instance_name"></a> [db\_instance\_name](#output\_db\_instance\_name) | Name of the default db |
| <a name="output_postgres_sg_id"></a> [postgres\_sg\_id](#output\_postgres\_sg\_id) | ID for the RDS security group |
| <a name="output_rds_instance_db_password"></a> [rds\_instance\_db\_password](#output\_rds\_instance\_db\_password) | Master RDS password for default postgres database |
| <a name="output_rds_instance_endpoint"></a> [rds\_instance\_endpoint](#output\_rds\_instance\_endpoint) | Endpoint for default postgres instance |
| <a name="output_rds_instance_username"></a> [rds\_instance\_username](#output\_rds\_instance\_username) | Master RDS username for core default postgres database |
| <a name="output_rds_master_credentials_secret_name"></a> [rds\_master\_credentials\_secret\_name](#output\_rds\_master\_credentials\_secret\_name) | Name for the secret in secrets manager used to hold default postgres master credentials |
<!-- END_TF_DOCS -->
