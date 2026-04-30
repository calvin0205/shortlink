output "users_table_name"     { value = aws_dynamodb_table.users.name }
output "users_table_arn"      { value = aws_dynamodb_table.users.arn }
output "devices_table_name"   { value = aws_dynamodb_table.devices.name }
output "devices_table_arn"    { value = aws_dynamodb_table.devices.arn }
output "incidents_table_name" { value = aws_dynamodb_table.incidents.name }
output "incidents_table_arn"  { value = aws_dynamodb_table.incidents.arn }
output "audit_table_name"     { value = aws_dynamodb_table.audit.name }
output "audit_table_arn"      { value = aws_dynamodb_table.audit.arn }
