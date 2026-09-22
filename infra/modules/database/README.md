# Database module

Creates PostgreSQL 16 on RDS across isolated data subnets. Storage, secrets and Performance Insights use a customer-managed rotating key. The database is private, forces TLS and lets RDS manage the master password in Secrets Manager.

The application uses a separate runtime secret populated after creating its limited database role. The one-shot schema bootstrap enables the supported `vector` extension with `CREATE EXTENSION`; the module does not set `shared_preload_libraries`.
