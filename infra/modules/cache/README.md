# Cache module

Creates an encrypted, private Redis OSS 7 replication group across two availability zones. `noeviction` preserves the Day 01 queue contract under pressure, while Multi-AZ failover reduces a single-node failure.

Redis remains coordination infrastructure, not the durable source of truth. The application recovery behavior documented on Day 01 still applies after failover or ambiguous enqueue responses.
