data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer" {
  name = "Managed-AllViewer"
}

data "aws_cloudfront_response_headers_policy" "security" {
  name = "Managed-SecurityHeadersPolicy"
}

resource "aws_cloudfront_distribution" "insighthub" {
  # checkov:skip=CKV_AWS_68:AWS WAF is outside the short-lived training lab threat model.
  # checkov:skip=CKV_AWS_86:Access logging would require a second durable log bucket for a short-lived lab.
  # checkov:skip=CKV_AWS_174:The CloudFront default certificate supplies AWS-managed TLS for the generated domain.
  # checkov:skip=CKV_AWS_305:A default root object would rewrite the dynamic Next.js root to a nonexistent static file.
  # checkov:skip=CKV_AWS_310:The lab has one temporary ALB origin and no second regional origin for failover.
  # checkov:skip=CKV_AWS_374:Geo-blocking is not part of the Day 03 training lab access policy.
  # checkov:skip=CKV2_AWS_42:A custom certificate is impossible without a controlled domain; the default domain remains browser-trusted.
  # checkov:skip=CKV2_AWS_47:A WAF Log4j managed rule is outside this short-lived fixture-mode lab with no Java workload.
  enabled         = true
  is_ipv6_enabled = true
  comment         = "Temporary HTTPS edge for the InsightHub Day 03 lab"
  price_class     = "PriceClass_100"

  origin {
    domain_name = var.origin_domain_name
    origin_id   = "insighthub-alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id           = "insighthub-alb"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.all_viewer.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security.id
    compress                   = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = var.tags
}
