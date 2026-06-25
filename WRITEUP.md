# WRITEUP — Kaggle Capstone: TroLyGiaoVu

**Kaggle track:** Agents for Good
**Submission deadline:** 06/07/2026
**Tác giả:** Phạm Thế An (anpt@dainam.edu.vn) — Đại học Đại Nam

---

## English Abstract

TroLyGiaoVu is a role-aware AI agent built with Google ADK 2.0 and Gemini Flash, designed to assist academic-affairs staff (cán bộ giáo vụ) at Dai Nam University, Vietnam. The system addresses two chronic pain points: (1) fragmented and time-consuming lookup of training regulations (quy chế đào tạo), and (2) error-prone manual construction of student make-up/retake course plans (lộ trình học lại). The agent enforces deterministic role-based access control, cites specific Articles and Clauses from source documents, logs every interaction for management reporting, and escalates out-of-scope requests to a human-in-the-loop queue. Evaluation on a 20-case Vietnamese dataset demonstrates correct citation grounding, proper refusal on out-of-scope queries, and accurate role-gate enforcement. This prototype is the technical foundation for a real-world rollout at Dai Nam University from August 2026 to June 2027.

---

## 1. Vấn đề (Problem Statement)

### Bối cảnh thực tế

Đại học Đại Nam hiện có khoảng vài nghìn sinh viên đào tạo theo hệ tín chỉ. Công tác giáo vụ phải xử lý hàng ngày nhiều loại yêu cầu từ sinh viên và giảng viên:

- **Tra cứu quy chế đào tạo:** Quy định về học lại, học cải thiện, trả nợ học phần, cảnh báo học vụ, điều kiện xét tốt nghiệp nằm rải rác trong nhiều văn bản PDF/Word chưa được số hoá và liên kết với nhau. Mỗi lần tra cứu mất 10–20 phút.
- **Lập lộ trình học lại / trả nợ học phần:** Cán bộ giáo vụ phải tổng hợp thủ công từ bảng điểm (Excel), chương trình đào tạo, lịch học, và quy định tiên quyết — rất dễ sai sót, đặc biệt khi có điều kiện tiên quyết phức tạp hoặc trùng lịch.
- **Báo cáo xử lý yêu cầu:** Không có hệ thống tổng hợp tự động, ban lãnh đạo khó theo dõi tải công việc và chất lượng tư vấn.

### Câu hỏi đặt ra

> Làm thế nào để xây dựng một trợ lý AI giúp cán bộ giáo vụ tra cứu quy chế chính xác có trích dẫn nguồn, lập lộ trình học lại tự động, đồng thời đảm bảo phân quyền truy cập và ghi nhật ký mọi yêu cầu?

---

## 2. Thiết kế giải pháp (Solution Design)

### Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLASK STAFF DASHBOARD                        │
│  [Chọn vai trò] [Tra cứu] [Lộ trình] [Lịch/Điểm] [Báo cáo]   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ POST /run  (JSON)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ADK FastAPI (fast_api_app.py)                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ SafetyPlugin                                            │   │
│  │  before_model_callback: quét prompt injection (VN+EN)  │   │
│  │  after_model_callback:  redact PII (mã SV, phone, mail)│   │
│  │  before_tool_callback:  kiem_tra_quyen(vai_tro, action) │   │
│  └───────────────────────────┬─────────────────────────────┘   │
└───────────────────────────────┼─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              WORKFLOW "giaovu_agent"  (agent.py)                │
│                                                                 │
│  START                                                          │
│    │                                                            │
│    ▼                                                            │
│  [intake]  LlmAgent  →  PhanLoaiYeuCau{loai, ma_sv, do_nhay_cam}│
│    │  output_key="phan_loai"                                    │
│    ▼                                                            │
│  [route_intake]  Python fn  →  Event(route=loai)               │
│    │                                                            │
│    ├── "tra_cuu_quy_che"   →  [reg_lookup]   LlmAgent          │
│    │                           tool: tra_cuu_quy_che()         │
│    │                           cite: [Điều X, Khoản Y]         │
│    │                                                            │
│    ├── "lo_trinh_hoc_lai"  →  [path_planner]  LlmAgent         │
│    │                           tools: lay_ho_so_sinh_vien()    │
│    │                                  lay_chuong_trinh_dao_tao()│
│    │                                  tinh_lo_trinh_hoc_lai()  │
│    │                                                            │
│    ├── "tra_cuu_lich_diem" →  [lich_diem]    LlmAgent          │
│    │                           tools: lay_lich_hoc()           │
│    │                                  lay_bang_diem()          │
│    │                                                            │
│    ├── "sinh_bieu_mau"     →  [form_filler]  LlmAgent          │
│    │                           tool: tao_bieu_mau()            │
│    │                                                            │
│    └── "ngoai_pham_vi"     →  [escalate]     Python fn         │
│                                → HITL queue (tiếng Việt)       │
│                                                                 │
│  [merge_log]  Python fn                                         │
│    tool: ghi_nhat_ky_yeu_cau()  →  nhat_ky_yeu_cau.csv         │
│    │                                                            │
│  END  →  response JSON                                          │
└─────────────────────────────────────────────────────────────────┘
                                │
          ┌─────────────────────┼──────────────────────┐
          ▼                     ▼                      ▼
    data/quy_che/        data/*.csv / .json      Cloud Trace
    (RAG retrieval)      (SV, CTĐT, lịch)        OTEL logs
```

### Các thành phần chính

| Thành phần | Công nghệ | Khái niệm khoá |
|-----------|-----------|----------------|
| ADK Workflow | google-adk 2.0 | Multi-agent, Coordinator/Router |
| Phân loại yêu cầu | LlmAgent + Pydantic | Structured output, output_key |
| Tra cứu quy chế | RAG (keyword+overlap) | Long-term memory, Tool |
| Lộ trình học lại | Python topo-sort + LlmAgent | Tool, tien_quyet, tín chỉ |
| Phân quyền | SafetyPlugin callbacks | Defense-in-depth, RBAC |
| Nhật ký & Báo cáo | ghi_nhat_ky_yeu_cau() | Agent Quality Flywheel |
| Đánh giá | agents-cli eval | Golden dataset, LLM-as-Judge |
| Deploy | Cloud Run | Stateless container |

---

## 3. Bản đồ khái niệm khoá — Day 1 đến Day 5

| Ngày | Khái niệm | Nơi thể hiện trong TroLyGiaoVu |
|------|-----------|-------------------------------|
| **Day 1** | Agent = Model + Tools + Orchestration + Deployment | Toàn bộ `app/agent.py`: Workflow + LlmAgent nodes |
| **Day 1** | Think-Act-Observe loop | Mỗi LlmAgent (intake, reg_lookup, path_planner) chạy vòng lặp ReAct |
| **Day 1** | Agent Levels 0-4 | Dự án đạt Level 3 (multi-agent + HITL); roadmap Level 4 với A2A |
| **Day 1** | Short-term memory (state scratchpad) | `output_key="phan_loai"` truyền phân loại qua các node |
| **Day 1** | Long-term memory (RAG) | `tra_cuu_quy_che()` đọc `data/quy_che/*.md` |
| **Day 1** | Multi-agent: Coordinator/Router | `route_intake` Python fn phân luồng theo loại |
| **Day 1** | HITL | Node `escalate` đẩy vào hàng đợi duyệt |
| **Day 1** | Security defense-in-depth | `SafetyPlugin` + `kiem_tra_quyen()` |
| **Day 2** | Function tools với typed params + docstring | Tất cả tools trong `app/tools.py` (ToolContext) |
| **Day 2** | Tool best practices: JSON output ngắn gọn | `tra_cuu_quy_che()` trả `{doan_van, nguon}` |
| **Day 2** | AgentTool | `path_planner` gọi `tinh_lo_trinh_hoc_lai()` |
| **Day 3** | Sessions & Events | ADK session + Event routing trong Workflow |
| **Day 3** | state via output_key | `phan_loai` shared giữa intake → route → specialists |
| **Day 3** | Memory Bank / PreloadMemoryTool | RAG qua `tra_cuu_quy_che()` |
| **Day 3** | Per-user ACL memory scope | `session.state["vai_tro"]` kiểm soát tool access |
| **Day 3** | Jinja2 system-instruction injection | `reg_lookup` inject tên cán bộ vào instruction |
| **Day 4** | SafetyPlugin before_model_callback | Quét prompt injection tiếng Việt + tiếng Anh |
| **Day 4** | after_model_callback PII redaction | Ẩn mã SV, email, số điện thoại khỏi output |
| **Day 4** | before_tool_callback guardrails | `kiem_tra_quyen()` chặn tool gọi ngoài quyền |
| **Day 4** | ADK Eval Set + agents-cli eval | `tests/eval/giaovu-dataset.json` 20 cases |
| **Day 4** | LLM-as-Judge metrics | `custom_response_quality` trong `eval_config.yaml` |
| **Day 4** | Python-function metrics | `co_trich_dan`, `tu_choi_dung`, `thuc_thi_phan_quyen` |
| **Day 4** | Agent Quality Flywheel | HITL feedback → eval cases mới → cải thiện model |
| **Day 5** | FastAPI + Cloud Run deploy | `fast_api_app.py` + `agents-cli deploy` |
| **Day 5** | Stateless container + externalized state | Session in-memory / Cloud SQL |
| **Day 5** | Web frontend / HITL dashboard | `frontend/` Flask + trang Hàng đợi duyệt |
| **Day 5** | Observability OTEL/Cloud Trace | `app_utils/telemetry.py` + Cloud Logging |
| **Day 5** | eval-gated deployment | CI/CD chạy eval trước khi push production |

---

## 4. Kết quả đánh giá (Eval Results)

> **Lưu ý:** Các chỉ số dưới đây là placeholder — cần điền sau khi chạy `agents-cli eval` lần đầu trên Kaggle/Cloud Run.

### Dataset: `tests/eval/datasets/giaovu-dataset.json`

| Loại eval case | Số lượng | Mô tả |
|---------------|----------|---------|
| Tra cứu quy chế | 7 | Câu hỏi về học lại, tiên quyết, cảnh báo học vụ |
| Lộ trình học lại | 5 | Nhập mã SV, xây kế hoạch từng kỳ |
| Tra cứu lịch/điểm | 3 | Lịch học tuần, bảng điểm học kỳ |
| Ngoài phạm vi | 2 | Kỳ vọng: từ chối/escalate |
| Adversarial | 3 | Prompt injection + role bị chặn |
| **Tổng** | **20** | |

### Kết quả metrics (placeholder — điền sau khi chạy eval)

| Metric | Mô tả | Kết quả |
|--------|-------|---------|
| `custom_response_quality` | Chất lượng câu trả lời tiếng Việt (LLM-as-Judge, 0–1) | `[PENDING]` |
| `agent_turn_count` | Số bước trung bình mỗi yêu cầu | `[PENDING]` |
| `co_trich_dan` | % câu trả lời có chứa "Điều" (trích dẫn quy chế) | `[PENDING]` |
| `tu_choi_dung` | % case ngoài phạm vi được từ chối đúng | `[PENDING]` |
| `thuc_thi_phan_quyen` | % case adversarial phân quyền bị chặn đúng | `[PENDING]` |

### Cách chạy để có kết quả thực:

```bash
uv pip install -e ".[eval]"
agents-cli eval tests/eval/datasets/giaovu-dataset.json \
  --config tests/eval/eval_config.yaml
```

---

## 5. Bảo mật & Phân quyền (Security)

### Mô hình phân quyền RBAC

```
Vai trò              Hành động được phép
──────────────────────────────────────────────────────────────────
tra_cuu_vien     →   tra_cuu_quy_che (read-only)
giao_vu          →   tra_cuu_quy_che, lay_ho_so_sinh_vien,
                     lay_chuong_trinh_dao_tao, tinh_lo_trinh_hoc_lai,
                     lay_lich_hoc, lay_bang_diem, tao_bieu_mau,
                     ghi_nhat_ky_yeu_cau
truong_phong_    →   Tất cả quyền trên + duyệt HITL queue +
dao_tao              xem toàn bộ nhat_ky_yeu_cau
```

### Các lớp bảo vệ (defense-in-depth)

1. **Tầng 1 — Phân loại trước (intake):** LlmAgent phân loại `do_nhay_cam` = "nhay_cam" khi yêu cầu liên quan đến dữ liệu cá nhân nhạy cảm.
2. **Tầng 2 — before_model_callback:** SafetyPlugin quét input tìm mẫu prompt injection bằng regex đa ngữ (VN + EN): `bỏ qua`, `ignore`, `quên hướng dẫn`, `system prompt`, v.v.
3. **Tầng 3 — before_tool_callback:** Gọi `kiem_tra_quyen(vai_tro, hanh_dong)` trước mỗi lần gọi tool. Từ chối bằng thông báo tiếng Việt cụ thể.
4. **Tầng 4 — after_model_callback:** Redact PII từ output: mã SV `\b\d{8,12}\b` (nếu vai trò không được phép), địa chỉ email, số điện thoại.
5. **Tầng 5 — Escalate:** Yêu cầu ngoài phạm vi hoặc nhạy cảm cao được đẩy vào HITL queue thay vì trả lời trực tiếp.

---

## 6. Triển khai (Deployment)

### Môi trường phát triển (Kaggle / local)

```
Python 3.11 + uv
google-adk[gcp] >= 2.0.0
Google AI Studio API key (GOOGLE_API_KEY)
agents-cli playground → http://localhost:8000
```

### Môi trường sản xuất (Cloud Run)

```
Docker (stateless container)
Cloud Run (us-east1, auto-scaling)
Cloud SQL / Firestore (externalized session state)
Cloud Trace + Cloud Logging (OTEL observability)
Artifact Registry (container images)
Secret Manager (GOOGLE_API_KEY, DB credentials)
```

### Lệnh deploy:

```bash
gcloud config set project YOUR_PROJECT_ID
agents-cli deploy
# Kết quả: https://giaovu-agent-XXXX-ue.a.run.app
```

---

## 7. Wow Factor — Báo cáo xử lý yêu cầu & Quality Flywheel

### Báo cáo xử lý yêu cầu (BÁO CÁO — Expected Product)

Mỗi yêu cầu được xử lý đều ghi vào `data/nhat_ky_yeu_cau.csv` qua `ghi_nhat_ky_yeu_cau()`. Trang **Báo cáo** trong Flask dashboard đọc CSV này và hiển thị:

- Tổng số yêu cầu theo loại (biểu đồ cột)
- Thời gian xử lý trung bình
- Danh sách yêu cầu cần duyệt HITL còn tồn đọng
- Xuất Excel để ban lãnh đạo xem xét

Đây là sản phẩm **"Báo cáo xử lý yêu cầu"** được liệt kê trong KPI thực tế của Đại học Đại Nam.

### Agent Quality Flywheel

```
Cán bộ dùng agent  ──►  Kết quả tốt/không tốt
         │                        │
         ▼                        ▼
  HITL queue (feedback)    ghi_nhat_ky_yeu_cau()
         │                        │
         └────────────┬───────────┘
                      ▼
           agents-cli eval generate
           (sinh eval cases mới từ lịch sử)
                      │
                      ▼
           agents-cli eval analyze
           (phát hiện điểm yếu)
                      │
                      ▼
           Cải thiện prompt / tools / data
                      │
                      ▼
           agents-cli eval (eval-gated deploy)
                      │
                      ▼
           Phiên bản tốt hơn lên Cloud Run
```

Vòng phản hồi này đảm bảo hệ thống tự cải thiện theo thực tế sử dụng tại Đại học Đại Nam — không cần đội kỹ thuật can thiệp thủ công.

---

## 8. Kết luận & Lộ trình thực tế

### Ý nghĩa của prototype Kaggle

Capstone này không chỉ là bài tập kỹ thuật. Đây là **prototype hoạt động** mà Phạm Thế An sẽ dùng để:

1. **Thuyết phục ban lãnh đạo Đại học Đại Nam** về tính khả thi của AI trong công tác giáo vụ.
2. **Thu thập dữ liệu thực** (quy chế đầy đủ, dữ liệu SV thực) để nâng cấp sau khi khoá học kết thúc.
3. **Đào tạo cán bộ giáo vụ** sử dụng hệ thống trong giai đoạn thí điểm (Q4/2026).

### Lộ trình triển khai thực tế (Aug 2026 – Jun 2027)

| Giai đoạn | Thời gian | Mục tiêu |
|-----------|-----------|----------|
| Số hoá quy chế | Aug – Sep 2026 | Chuyển toàn bộ quy chế sang Markdown, nhập CTĐT thực |
| Thí điểm nội bộ | Oct – Dec 2026 | 2–3 cán bộ giáo vụ dùng thực tế, thu nhật ký |
| Đánh giá & cải thiện | Jan – Mar 2027 | Chạy Quality Flywheel, nâng cấp model |
| Mở rộng | Apr – Jun 2027 | Toàn bộ phòng Đào tạo + tích hợp hệ thống QLSV |

**Chủ sở hữu:** Phạm Thế An (anpt@dainam.edu.vn)
**KPIs thực tế cần đạt:**
- Giảm 50% thời gian tra cứu quy chế (từ ~15 phút xuống ~3 phút)
- Giảm 80% sai sót khi lập lộ trình học lại
- 100% yêu cầu được ghi nhật ký và có thể báo cáo

---

*Writeup này được viết theo format Kaggle Notebooks. Kết quả eval thực tế sẽ được cập nhật trước deadline 06/07/2026.*
