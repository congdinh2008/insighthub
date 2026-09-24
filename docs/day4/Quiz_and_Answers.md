# Day 04 quiz and answers

This is the repository practice quiz. Official class-form evidence remains separate.

1. Why is a ServiceMonitor present but a target still absent?
   - Prometheus must select the ServiceMonitor namespace and labels; the ServiceMonitor must select the Service labels; its endpoint port must match the named Service port. Inspect generated Prometheus config and rejected resources.
2. Why use a one-hour offset baseline and a two-minute `for`?
   - The offset reduces contamination by the current incident. The `for` rejects short spikes. Neither proves the baseline is representative; missing data and minimum volume still need guards.
3. What makes an AI RCA evidence-first?
   - It cites actual metric names, labels, timestamps and values; separates observed/inferred/unknown; proposes falsifiable checks; and does not claim causality from correlation alone.
4. How do data drift and concept drift differ, and should DevOps auto-retrain?
   - Data drift changes input distribution; concept drift changes the input-target relationship. DevOps should not independently retrain/promote from input drift. It operates an owner-defined pipeline with labels/proxies, gates and approvals.
5. What must be rolled back with a model?
   - The compatible model bundle: weights, tokenizer/preprocessing, features, schema, runtime, cache and index. InsightHub embedding identity changes require a matching index and reindex/migration.

Practice result: 5/5 after self-review. This does not replace the official quiz form required by the specification.
