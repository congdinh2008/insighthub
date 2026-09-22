# AWS bootstrap

This root is the only Day 03 operation initially run with a reviewed short-lived operator session. It creates an encrypted/versioned state bucket, native S3 lock support and a GitHub OIDC deployment role bound to one protected GitHub Environment.

The caller supplies a customer-managed deployment policy that has already been reviewed for the selected sandbox account. The root rejects the AWS `AdministratorAccess` managed policy. This separation avoids hiding a broad lab permission set inside reusable student source.

The bootstrap root keeps local state until it is migrated to the protected bucket using a reviewed `terraform init -migrate-state` operation. Do not delete the bucket, key or role until every dependent state has been destroyed and the required audit record has been retained.
