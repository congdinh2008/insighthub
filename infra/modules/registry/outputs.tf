output "repository_urls" {
  description = "Workload repository URLs."
  value       = { for name, repository in aws_ecr_repository.this : name => repository.repository_url }
}
