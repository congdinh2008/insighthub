# Day 4 — Tài liệu đọc trước · Topic 3
# MLOps Overview cho DevOps Engineer

> **Thời gian đọc:** ~20 phút
> **Lưu ý:** Đây là **overview nhận thức** — không phải hướng dẫn train model. Mục tiêu: bạn biết đủ MLOps để *phối hợp* với ML team, không phải tự làm việc của họ.

---

## 1. Lý thuyết cơ bản

### 1.1. Vì sao DevOps cần biết MLOps

Năm 2026, gần như mọi sản phẩm đều có một thành phần AI/ML — InsightHub dùng
LLM + embedding model. Khi một service có model bên trong, **vận hành nó khác với
vận hành một service thường**. DevOps engineer không train model, nhưng là người
**deploy, serve, observe và rollback** nó. Nếu không hiểu vòng đời model, bạn sẽ
không biết phải dựng hạ tầng gì cho ML team.

Câu hỏi định hướng cả Topic này: *"Khi ML team bảo model bị drift, DevOps làm gì?"*

### 1.2. "Model là một service" — góc nhìn DevOps

Cách tư duy đúng nhất cho DevOps: **coi model như một service** — nó có version,
có latency, có cost, có thể lỗi, cần monitor và rollback. Toàn bộ "MLOps" mà một
DevOps engineer cần chính là: *deploy model như một service, observe nó như
observe service khác.* Phần Kubeflow/MLflow/train pipeline nằm **ngoài** phạm vi
vai trò DevOps.

### 1.3. App Artifact vs Model Artifact

| Chiều | App Artifact (Docker image) | Model Artifact (`.pt`, `.pkl`, `.onnx`) |
|---|---|---|
| **Tạo bởi** | CI/CD (git push → build) | Training pipeline (data → GPU → experiment) |
| **Version bởi** | Git commit SHA, image tag | Model registry (MLflow, W&B, Vertex AI) |
| **Test bởi** | Unit/integration test | Evaluation metrics (accuracy, F1, latency@p95) |
| **Deploy bởi** | Helm / kubectl | Model serving (Triton, BentoML, SageMaker) |
| **Rollback** | Image tag trước | Model version trước trong registry |
| **Suy thoái** | Code rot (CVE dependency) | **Model drift** (data distribution đổi) |

**Khác biệt cốt lõi:** code **không tự tệ hơn** theo thời gian; model **thì có**.
Model artifact có thêm một lifecycle phase mà app artifact không có — **drift
detection**.

---

## 2. Concept & Core Components

### 2.1. ML Lifecycle Map — DevOps đứng ở đâu

```
Data Collection → Feature Engineering → Model Training
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
                                  (loop về Training)
```

**4 stage DevOps own PRIMARY:**
1. **CI/CD cho training pipeline** — trigger, lưu artifact (không viết training logic).
2. **Model Serving Infrastructure** — K8s deployment, scaling, health check.
3. **Monitoring Infrastructure** — Prometheus/Grafana cho model metrics.
4. **Rollback Mechanism** — tự động rollback khi performance tụt.

**ML Engineer own:** training logic, feature selection, hyperparameters, ngưỡng
eval metrics. Hai vai trò gặp nhau ở **registry** và **approval gate**.

### 2.2. Model Registry — "Docker Registry cho model"

Lưu model binary + training metadata (dataset version, hyperparameters, git
commit) + evaluation metrics + stage (`Staging` → `Production` → `Archived`).
Phổ biến: MLflow Model Registry, W&B Artifacts, Vertex AI / SageMaker Model
Registry.

### 2.3. Approval Gate — vì sao không deploy thẳng

Không promote model từ training thẳng lên production vì:
1. Model mới có thể **regression** trên edge case không có trong eval set.
2. Model ảnh hưởng **business metrics** (revenue, conversion) — cần sign-off.
3. **Regulatory compliance** (banking, healthcare) yêu cầu human approval.

**Pattern chuẩn:**
```
Train → Auto-eval (accuracy > threshold?) → Staging deploy
     → A/B test hoặc shadow mode (1-5 ngày)
     → Human review metrics → Approval → Production promote
```
**DevOps role:** *build* cái gate và pipeline promotion — **không** quyết định
approve/reject.

---

## 3. Features — 2 loại Drift & ranh giới xử lý

### 3.1. Data Drift vs Concept Drift

| | Data Drift | Concept Drift |
|---|---|---|
| **Định nghĩa** | Phân phối input thay đổi | Quan hệ input→output thay đổi |
| **Ví dụ InsightHub** | User upload tài liệu kỹ thuật nhiều hơn thay vì policy docs | Embedding space đổi → retrieval kém chính xác hơn |
| **Phát hiện** | Statistical test (KL divergence, PSI) trên feature distribution | Model performance metric giảm (accuracy, user feedback) |
| **Fix** | Retrain với data mới | Retrain với data relabel/augment |

### 3.2. Ownership Boundary — Drift fire thì ai làm gì?

```
Drift alert fire
   ↓ ML Engineer: điều tra, quyết định có retrain không
   ↓ ML Engineer: retrain → push model mới lên Registry
   ↓ DevOps: CI/CD chạy eval gate → promote lên Staging
   ↓ ML Engineer + Product: review Staging → approve
   ↓ DevOps: promote Registry stage → Production rollout
   ↓ DevOps: monitor production, rollback nếu regression
```

> **DevOps KHÔNG BAO GIỜ:** tự quyết định retrain, sửa training code, đổi eval
> threshold. **Rollback là tự động (DevOps own); retrain là thủ công (ML own).**

### 3.3. Automated Rollback — điểm DevOps own hoàn toàn

```yaml
# Prometheus alert cho model regression (ví dụ)
- alert: ModelPerformanceDrop
  expr: model_accuracy_5m < 0.85 and model_request_count_5m > 100
  for: 5m
  # → trigger: kubectl set image deployment/model-serving model=<previous_version>
  # → notify ML team
```
Đây chính là điểm MLOps **gặp** Day 4: model cũng là một service được Prometheus
observe; rollback chạy trên cùng hạ tầng alert bạn vừa dựng.

---

## 4. Implementation — liên hệ với InsightHub

InsightHub gọi LLM + embedding qua **provider API** (Gemini/Anthropic) — tức là
"model-as-a-service" do bên thứ ba serve. Bạn không train chúng, nhưng vẫn phải:
- **Observe** chúng như service: `insighthub_llm_call_latency_seconds`,
  `insighthub_llm_tokens_total` (đã instrument từ Topic 1).
- **Phát hiện bất thường**: latency spike = provider chậm/rate limit (đã làm ở
  phần anomaly detection).
- **Có phương án rollback/fallback**: đổi provider (`LLM_PROVIDER`) khi một nhà
  cung cấp lỗi — đúng tinh thần "model là service có thể fail".

Nếu sau này InsightHub tự host một embedding model, *toàn bộ* lifecycle ở Mục 2
sẽ áp dụng — và vai trò DevOps vẫn nằm đúng ở 4 stage primary đã nêu.

---

## 5. Best Practices

1. **Coi model là service** — version, latency, cost, rollback như mọi service.
2. **Build the gate, don't be the gate** — DevOps dựng approval pipeline, ML team quyết định.
3. **Rollback tự động, retrain thủ công** — đừng để pipeline tự retrain.
4. **Observe model bằng đúng stack Day 4** — Prometheus/Grafana, không công cụ riêng.
5. **Phân biệt rõ ownership** — biết khi nào "đây là việc của ML team".

### Anti-patterns

| Anti-pattern | Hậu quả |
|---|---|
| DevOps tự retrain model khi thấy drift | Vượt vai trò; sai vì không nắm training logic |
| Deploy model thẳng từ training lên prod | Bỏ qua eval/approval → regression lọt prod |
| Không version model artifact | Không rollback được khi model mới tệ hơn |
| Coi model như code tĩnh | Bỏ sót drift — "code không tự tệ, model thì có" |

---

## 6. Case Study — Drift alert lúc 2h sáng: ai làm gì?

**Bối cảnh:** Một công ty fintech serve model chấm điểm tín dụng. 2h sáng,
`model_accuracy_5m` tụt từ 0.91 xuống 0.82 — alert fire.

**Nếu DevOps làm sai (anti-pattern):** on-call DevOps thấy "accuracy thấp", tự
chạy lại script training với data mới nhất, promote thẳng lên production. Sáng ra
ML team phát hiện model mới train trên data chưa được clean → còn tệ hơn. Mất
niềm tin, phải rollback khẩn.

**Nếu đúng ranh giới ownership:**
1. **DevOps (tự động):** alert fire → rollback script đưa model về version trước
   (`kubectl set image ... model=v1.4.2`) → accuracy về 0.91 → **hết cháy**.
2. **DevOps:** notify ML team kèm evidence (metric + timestamp).
3. **ML Engineer (sáng hôm sau):** điều tra → phát hiện **data drift** (một nguồn
   dữ liệu đầu vào đổi format) → retrain đúng cách → push lên Registry.
4. **DevOps:** pipeline chạy eval gate → Staging → ML+Product approve → promote.

**Bài học:** DevOps **vá nhanh** bằng rollback tự động (đúng việc), nhưng **không
sửa gốc** bằng cách tự retrain (sai việc). Ranh giới này — *rollback tự động,
retrain thủ công* — là điều quan trọng nhất một DevOps engineer cần nhớ về MLOps.

---

## Tự kiểm tra trước buổi học

1. "Model là một service" nghĩa là gì với DevOps?
2. Khác biệt cốt lõi giữa app artifact và model artifact?
3. Data drift vs concept drift — cho ví dụ với InsightHub.
4. Khi drift alert fire, DevOps làm gì *đầu tiên*? Có tự retrain không?
5. Vì sao "rollback tự động nhưng retrain thủ công"?
6. 4 stage nào DevOps own PRIMARY trong ML lifecycle?

---

## Đọc thêm (tùy chọn)

- Google — MLOps: Continuous delivery and automation pipelines in ML
- `mlops-overview-notes.md` (bản artifact tóm tắt dạng bảng — dùng khi ôn nhanh)
- MLflow Model Registry docs
