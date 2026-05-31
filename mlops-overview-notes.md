# MLOps Overview — Module 7 Day 4 Notes

> **Đối tượng**: DevOps Engineer cần biết đủ MLOps để phối hợp với ML team — không cần tự train model.
> **Mục tiêu**: Sau 25 phút, có thể trả lời: "Khi ML team bảo model drift, DevOps làm gì?"

---

## Block 1 — Mindset: App Artifact vs Model Artifact

| Chiều | App Artifact (Docker image) | Model Artifact (`.pt`, `.pkl`, `.onnx`) |
|---|---|---|
| **Tạo ra bởi** | CI/CD (git push → build) | Training pipeline (data → GPU → experiment) |
| **Version bởi** | Git commit SHA, image tag | Model registry (MLflow, W&B, Vertex AI) |
| **Test bởi** | Unit test, integration test | Evaluation metrics (accuracy, F1, latency@P95) |
| **Deploy bởi** | Helm / kubectl | Model serving (Triton, BentoML, SageMaker Endpoint) |
| **Rollback** | Previous image tag | Previous model version in registry |
| **Decay** | Code rot (dependency CVE) | Model drift (data distribution shift) |

**Key insight**: Model artifact có thêm một lifecycle phase mà app artifact không có — **drift detection**. Code không tự "tệ hơn" theo thời gian; model thì có.

**DevOps ownership**: Quản lý **infrastructure** (K8s, CI/CD, serving infra) — không sở hữu model logic.

---

## Block 2 — Lifecycle: ML Lifecycle Map

```
Data Collection → Feature Engineering → Model Training
       ↓                  ↓                   ↓
   Data Quality       Feature Store       Experiment Tracking
  (Great Expectations) (Feast, Tecton)    (MLflow, W&B)
                                               ↓
                                    Model Registry (versioned)
                                               ↓
                                    Approval Gate (human review)
                                               ↓
                                    Model Serving (online/batch)
                                               ↓
                                    Production Monitoring
                                               ↓
                                    Drift Detection ──→ Retrain trigger
                                               ↓
                                    (loop trở lại Training)
```

**4 stage DevOps own PRIMARY:**
1. **CI/CD** cho training pipeline (trigger, artifact storage)
2. **Model Serving Infrastructure** (K8s deployment, scaling, health check)
3. **Monitoring Infrastructure** (Prometheus, Grafana cho model metrics)
4. **Rollback Mechanism** (automated rollback khi model performance drop)

**ML Engineer owns**: Training logic, feature selection, hyperparameters, eval metrics thresholds.

---

## Block 3 — Registry & Approval Gate

### Model Registry

Tương tự Docker Registry nhưng cho model artifacts. Lưu:
- Model binary (`.pt`, `.pkl`, `.onnx`)
- Training metadata (dataset version, hyperparameters, git commit)
- Evaluation metrics (accuracy, latency, resource usage)
- Stage: `Staging` → `Production` → `Archived`

**Phổ biến**: MLflow Model Registry, W&B Artifacts, Vertex AI Model Registry, SageMaker Model Registry.

### Approval Gate — Tại sao cần?

Không deploy model trực tiếp từ training lên production vì:
1. Model mới có thể có **regression** trên edge cases không có trong eval set
2. Model ảnh hưởng **business metrics** (revenue, conversion) — cần sign-off
3. **Regulatory compliance** (banking, healthcare) yêu cầu human approval trước deploy

**Pattern chuẩn**:
```
Train → Auto-eval (accuracy > threshold?) → Staging deploy
     → A/B test hoặc shadow mode (1-5 ngày)
     → Human review metrics → Approval
     → Production promote
```

**DevOps role**: Build CI/CD pipeline thực hiện gate check và promotion, không decide có approve không.

---

## Block 4 — Drift Detection & Rollback

### 2 loại Drift

| | Data Drift | Concept Drift |
|---|---|---|
| **Định nghĩa** | Input data distribution thay đổi | Relationship giữa input và output thay đổi |
| **Ví dụ InsightHub** | Users upload tài liệu kỹ thuật nhiều hơn thay vì policy docs | Embedding space thay đổi → retrieval chính xác thấp hơn |
| **Phát hiện bởi** | Statistical test (KL divergence, PSI) trên feature distribution | Model performance metrics giảm (accuracy, user feedback) |
| **Fix** | Retrain với data mới | Retrain với relabeled/augmented data |

### Ownership Boundary — Drift fire thì ai làm gì?

```
Drift alert fire
      ↓
ML Engineer: điều tra root cause, quyết định có cần retrain không
      ↓
ML Engineer: retrain model với data mới → push to Model Registry
      ↓
DevOps: CI/CD pipeline chạy eval gate → promote lên Staging
      ↓
ML Engineer + Product: review Staging metrics → approve
      ↓
DevOps: promote Model Registry stage → Production rollout
      ↓
DevOps: monitor production metrics, rollback nếu regression
```

**DevOps KHÔNG BAO GIỜ**: tự quyết định retrain model, sửa training code, thay đổi eval thresholds.

### Automated Rollback

Nếu model production metrics drop sau deploy:

```python
# Ví dụ: Prometheus alert rule cho model regression
- alert: ModelPerformanceDrop
  expr: |
    model_accuracy_5m < 0.85
    AND model_request_count_5m > 100
  for: 5m
  # → trigger rollback script
  # → `kubectl set image deployment/model-serving model=previous_version`
  # → notify ML team
```

**Key principle**: Rollback là automatic (DevOps owns), retrain là manual (ML Engineer owns).

---

## Ownership Summary Table

| Stage | DevOps PRIMARY | ML Engineer PRIMARY | Shared |
|---|---|---|---|
| Data collection | ✗ | ✓ | Infra |
| Feature engineering | ✗ | ✓ | Pipelines |
| Model training | ✗ | ✓ | Compute infra |
| Model registry | CI/CD automation | Eval thresholds | ✓ |
| **Approval gate** | Build the gate | Approve/reject | ✓ |
| **Model serving** | ✓ (K8s, scaling) | Serving config | ✓ |
| **Monitoring infra** | ✓ (Prometheus/Grafana) | Business metrics definition | ✓ |
| **Drift detection** | Alert infra | Detection logic | ✓ |
| **Rollback** | ✓ (automated) | Define threshold | ✓ |
| Retrain | ✗ (NEVER) | ✓ | ✗ |

---

## Quick Quiz (Self-check)

1. App artifact vs Model artifact — sự khác biệt quan trọng nhất?  
   → **Decay**: model drift theo thời gian, code không.

2. Data drift vs Concept drift?  
   → Data drift: input distribution thay đổi. Concept drift: input→output relationship thay đổi.

3. Nếu Drift alert fire, DevOps làm gì đầu tiên?  
   → Notify ML Engineer. KHÔNG tự retrain.

4. Tại sao cần Approval Gate trước khi promote lên Production?  
   → Auto-eval không cover mọi edge case; business + regulatory sign-off.

5. Khi nào DevOps tự rollback model mà không cần ML Engineer?  
   → Khi model performance metrics (Prometheus) drop dưới threshold sau deploy — rollback automatic, nhưng vẫn notify ML team.
