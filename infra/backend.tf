terraform {
  backend "s3" {
    # Supply bucket, key, and region with -backend-config during terraform init.
    # The state bucket is bootstrapped separately from this root module.
    encrypt      = true
    use_lockfile = true
  }
}
