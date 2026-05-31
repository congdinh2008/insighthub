# Backend config — values passed via -backend-config flags or backend.hcl files
# Usage:
#   terraform init -backend-config=backend-dev.hcl
#   terraform init -backend-config=backend-prod.hcl
#
# Example backend-dev.hcl:
#   bucket         = "insighthub-tfstate-dev"
#   key            = "insighthub/dev/terraform.tfstate"
#   region         = "ap-southeast-1"
#   encrypt        = true
#   dynamodb_table = "insighthub-tflock-dev"
#   kms_key_id     = "alias/insighthub-terraform"
terraform {
  backend "s3" {}
}
