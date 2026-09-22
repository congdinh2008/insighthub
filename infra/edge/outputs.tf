output "https_url" {
  description = "Trusted HTTPS endpoint using the CloudFront default certificate."
  value       = "https://${aws_cloudfront_distribution.insighthub.domain_name}"
}

output "distribution_id" {
  description = "Distribution identifier used during teardown verification."
  value       = aws_cloudfront_distribution.insighthub.id
}
