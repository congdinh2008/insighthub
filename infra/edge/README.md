# Temporary HTTPS edge

This root creates a minimum CloudFront distribution after the Helm Ingress has produced an ALB hostname. It supplies a browser-trusted `cloudfront.net` HTTPS endpoint when the lab account has no domain or ACM certificate.

The origin remains an ephemeral HTTP ALB. The distribution disables caching and forwards every method/header so upload, polling and chat preserve their API semantics. Destroy this root before deleting the Ingress and core infrastructure.
