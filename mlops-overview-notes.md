# Day 04 - MLOps overview notes

These notes cover architecture and ownership only. No ML platform or training pipeline was implemented in Day 04.

## Block 1 - Application artifact and model artifact

| Dimension | Application | Model system |
|---|---|---|
| Artifact | image, binary, config and dependency lock | model weights plus tokenizer/preprocessing, feature/schema and evaluation metadata |
| Version identity | image digest and source commit | immutable model version/digest, dataset/feature lineage and training code |
| Quality | functional, security, performance and availability tests | overall and slice quality, calibration, latency/resource and robustness tests |
| Compatibility | API/schema/runtime compatibility | serving runtime, input/output schema, feature pipeline, cache and index compatibility |

A model alias such as champion is mutable. A deployment audit must store the resolved immutable version. For InsightHub embeddings, equal vector dimensions do not mean equal semantic space; provider/model/endpoint/revision changes require a compatible index and migration/reindex.

## Block 2 - Lifecycle and ownership

`Data -> prepare/features -> train -> validate -> registry -> release gate -> deploy -> monitor -> retrain decision`

| Stage | Primary owner | DevOps responsibility |
|---|---|---|
| dataset, labels, relevance | ML and domain owner | access, storage and reproducible platform |
| training/evaluation logic | ML | pipeline runtime, compute and artifact transport |
| registry infrastructure | Platform/DevOps | availability, access, audit and immutable artifact handling |
| release decision | assigned product/model owner | present trustworthy gate evidence; do not silently promote |
| rollout/availability | DevOps | progressive deployment, observability and rollback mechanism |
| drift/quality investigation | ML and domain | preserve model/data versions and operational telemetry |
| retrain workflow | owner-defined pipeline | execute the assigned workflow; do not choose new labels/objectives independently |

DevOps can operate a retraining job that has an approved trigger, owner and gate. DevOps does not decide to retrain or promote only because one input metric changed.

## Block 3 - Registry, approval gate, drift and rollback

- Registry stores immutable versions, metadata and lineage. A mutable alias is resolved and audited at deployment.
- Approval Gate uses criteria defined before evaluation. Missing or invalid metrics fail closed. Evidence covers dataset split/leakage, slices, latency/resources, schema and uncertainty, not only one average score.
- Data drift means the input distribution changed. Concept drift means the relationship between input and target changed. Input statistics alone cannot prove concept drift or degraded quality; delayed labels and proxies must be explicit.
- Rollback restores a compatible bundle: model, tokenizer/preprocessing, features, schema, runtime, cache and index. Rolling back only weights can leave an incompatible serving system.

## Block 4 - Release decision case

Assume a reranker candidate changes overall NDCG@10 from 0.72 to 0.75, Vietnamese slice NDCG@10 from 0.70 to 0.62 and serving p95 from 80 ms to 180 ms. The defined gates allow no overall decrease, at most 0.02 absolute Vietnamese-slice decrease and p95 no greater than 120 ms.

Decision: do not promote. The slice falls by 0.08 and p95 exceeds the gate by 60 ms. Before a later decision, collect sample sizes and uncertainty, validate dataset/slice representativeness, confirm identical evaluation protocol and confirm that gates were fixed before observing the candidate. The owner decides after evidence review; DevOps keeps the candidate version available but does not bypass the gate.
