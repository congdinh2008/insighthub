bucket         = "insighthub-tfstate-dev"
key            = "insighthub/dev/terraform.tfstate"
region         = "ap-southeast-1"
encrypt        = true
dynamodb_table = "insighthub-tflock-dev"
kms_key_id     = "alias/insighthub-terraform"
