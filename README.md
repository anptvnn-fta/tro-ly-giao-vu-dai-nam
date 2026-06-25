# TroLyGiaoVu — Trợ lý Giáo vụ số Đại Nam

Hệ thống trợ lý AI hỗ trợ cán bộ giáo vụ Đại học Đại Nam tra cứu quy chế đào tạo, lập lộ trình học lại, và tổng hợp báo cáo xử lý yêu cầu.

**Chủ sở hữu sáng kiến:** Phạm Thế An (anpt@dainam.edu.vn) — triển khai thực tế Aug 2026 – Jun 2027.
**Kaggle track:** Agents for Good | Hạn nộp: 06/07/2026.

---

## Cấu trúc thư mục

```
Capstone_GiaoVu_DaiNam/
├── app/
│   ├── agent.py              # ADK Workflow "giaovu_agent" (nodes + routing)
│   ├── tools.py              # Tất cả function tools (tra cứu, lộ trình, biểu mẫu)
│   ├── safety.py             # SafetyPlugin (phân quyền, PII redaction, chống injection)
│   ├── fast_api_app.py       # FastAPI app (ADK + /feedback endpoint)
│   └── app_utils/
│       ├── telemetry.py      # OTEL / Cloud Trace
│       └── typing.py         # Pydantic types (Feedback, PhanLoaiYeuCau...)
├── frontend/
│   ├── __init__.py
│   ├── app.py                # Flask staff dashboard (dark theme)
│   └── templates/
│       ├── base.html
│       ├── tra_cuu.html      # Trang tra cứu quy chế (chat)
│       ├── lo_trinh.html     # Lộ trình học lại (nhập mã SV)
│       ├── lich_diem.html    # Lịch học & bảng điểm
│       ├── hang_doi.html     # Hàng đợi duyệt HITL
│       └── bao_cao.html      # Báo cáo xử lý yêu cầu
├── data/
│   ├── quy_che/
│   │   ├── quy_che_dao_tao.md       # Quy chế tín chỉ (Điều/Khoản)
│   │   └── quy_dinh_hoc_phi.md      # Học phí tín chỉ, học lại
│   ├── chuong_trinh_dao_tao.json    # CTĐT ngành CNTT
│   ├── sinh_vien_diem.csv           # Dữ liệu SV + điểm
│   ├── lich_hoc.csv                 # Lịch học theo môn/kỳ
│   └── nhat_ky_yeu_cau.csv          # Nhật ký yêu cầu (nguồn Báo cáo)
├── tests/
│   ├── unit/                        # Unit tests cho tools, safety
│   └── eval/
│       ├── datasets/
│       │   └── giaovu-dataset.json  # 20 eval cases
│       └── eval_config.yaml         # Metrics: trích dẫn, từ chối, phân quyền
├── agents-cli-manifest.yaml
├── pyproject.toml
├── README.md               ← (file này)
├── WRITEUP.md              # Kaggle Writeup
├── VIDEO_SCRIPT.md         # Kịch bản demo 3 phút
└── ANTIGRAVITY_PROMPTS.md  # Hướng dẫn vibe-code lại trong Antigravity
```

---

## Yêu cầu môi trường

| Công cụ | Phiên bản | Ghi chú |
|---------|-----------|--------|
| Python | >=3.11, <3.14 | Quản lý bằng `uv` |
| uv | latest | `pip install uv` |
| google-agents-cli | >=0.5.0 | `uv tool install google-agents-cli` |
| Google Cloud SDK | latest | Cần cho Cloud Run deploy |
| Google AI Studio API key | — | Dùng để chạy local (thay thế ADC) |

### Cài đặt

```bash
# Cài agents-cli và skills
uvx google-agents-cli setup

# Vào thư mục dự án
cd Capstone_GiaoVu_DaiNam

# Cài dependencies
agents-cli install
```

---

## Biến môi trường

Tạo file `.env` trong thư mục `Capstone_GiaoVu_DaiNam/` (không commit lên Git):

```dotenv
# Bắt buộc — chọn MỘT trong hai phương thức xác thực:

# Cách 1: Google AI Studio API key (dùng để chạy local, không cần GCP project)
GOOGLE_API_KEY=AIza...

# Cách 2: Application Default Credentials (dùng khi deploy trên Cloud Run)
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# --- Tuỳ chọn ---
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-east1

# Artifact / Session storage (để trống = in-memory khi chạy local)
ARTIFACT_STORAGE_URI=gs://your-bucket/artifacts
SESSION_SERVICE_URI=

# Phân quyền mặc định khi chạy playground (giao_vu | truong_phong_dao_tao | tra_cuu_vien)
DEFAULT_VAI_TRO=giao_vu

# Flask frontend
FLASK_SECRET_KEY=change-me-in-production
ADK_API_BASE_URL=http://localhost:8000
```

> **Lưu ý bảo mật:** Không bao giờ commit `GOOGLE_API_KEY` lên repository công khai.
> Trên Cloud Run, dùng Secret Manager thay cho biến môi trường trực tiếp.

---

## Chạy local

### 1. Playground (ADK dev server + giao diện chat)

```bash
# Chạy ADK playground (tự reload khi sửa agent.py / tools.py)
agents-cli playground
# Mở trình duyệt: http://localhost:8000
```

### 2. Flask staff dashboard

```bash
# Trong terminal thứ hai (ADK server đã chạy ở cổng 8000)
cd Capstone_GiaoVu_DaiNam
uv run python -m frontend.app
# Mở: http://localhost:5000
```

### 3. Chạy với ADK CLI trực tiếp

```bash
uv run adk run app
# Hoặc dùng API server:
uv run adk api_server app --port 8000
```

---

## Đánh giá (Eval)

```bash
# Cài thêm optional deps cho eval
uv sync --extra eval

# (nếu 'agents-cli' chưa có trên PATH) cài tool, hoặc thay bằng 'uvx google-agents-cli'
uv tool install google-agents-cli

# Chạy eval: sinh trace (chạy agent) rồi chấm điểm — CẦN GOOGLE_API_KEY
agents-cli eval run \
  --dataset tests/eval/datasets/giaovu-dataset.json \
  --config tests/eval/eval_config.yaml

# Phân tích cụm lỗi từ kết quả
agents-cli eval analyze
```

Các metrics được đo:
- `custom_response_quality` — chất lượng tiếng Việt, độ chính xác
- `agent_turn_count` — số bước suy luận
- `co_trich_dan` — câu trả lời có trích dẫn "Điều X, Khoản Y"
- `tu_choi_dung` — từ chối đúng khi không có quy định
- `thuc_thi_phan_quyen` — phân quyền được thực thi đúng

---

## Triển khai lên Cloud Run

### Bước 1 — Cấu hình GCP

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login
```

### Bước 2 — Bật các API cần thiết (1 lần)

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### Bước 3 — Deploy (build trên Cloud Build, KHÔNG cần Docker local)

```bash
gcloud run deploy tro-ly-giao-vu \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars GOOGLE_API_KEY=YOUR_AI_STUDIO_KEY,GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

Sau khi xong, gcloud in ra URL công khai dạng
`https://tro-ly-giao-vu-XXXXXXXX-as.a.run.app` — đây là **link dự án** để nộp Kaggle.
Mở URL kèm `/dev-ui/` để vào giao diện chat ADK (chọn agent `app`).

> 🔐 Production nên dùng Secret Manager thay vì đặt key trực tiếp:
> `--set-secrets GOOGLE_API_KEY=GIAOVU_KEY:latest`

### Bước 4 (tuỳ chọn) — CI/CD + Terraform

```bash
agents-cli scaffold enhance
agents-cli infra cicd
```

---

## Kiến trúc tóm tắt

```
Cán bộ giáo vụ
      │ HTTP request
      ▼
┌─────────────────────┐
│  Flask Dashboard    │  (frontend/)
│  Chọn vai trò       │
└────────┬────────────┘
         │ POST /run
         ▼
┌─────────────────────────────────────────────┐
│  ADK FastAPI App (fast_api_app.py)          │
│  SafetyPlugin: injection scan + PII redact  │
│  before_tool_callback: kiem_tra_quyen()     │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Workflow "giaovu_agent"                    │
│                                             │
│  intake ──► route_intake                   │
│                 │                           │
│    ┌────────────┼─────────────┐             │
│    ▼            ▼             ▼             │
│ reg_lookup  path_planner  lich_diem         │
│ form_filler   escalate                      │
│    └────────────┴──────► merge_log          │
└─────────────────────────────────────────────┘
         │
         ▼
┌────────────────┐   ┌──────────────────────┐
│  data/ (CSV,   │   │  Cloud Trace / OTEL  │
│  JSON, MD)     │   │  nhat_ky_yeu_cau.csv │
└────────────────┘   └──────────────────────┘
```

---

## Phân quyền (Roles)

| Vai trò | Quyền |
|---------|-------|
| `tra_cuu_vien` | Chỉ tra cứu quy chế (`reg_lookup`) |
| `giao_vu` | Tra cứu + lập lộ trình học lại + tra cứu lịch/điểm + tạo biểu mẫu |
| `truong_phong_dao_tao` | Toàn quyền + duyệt hàng đợi HITL |

Vai trò được đọc từ `session.state["vai_tro"]` và kiểm tra trong `before_tool_callback` của `SafetyPlugin`.

---

## Liên hệ & đóng góp

- **Chủ dự án:** Phạm Thế An — anpt@dainam.edu.vn
- **Tổ chức:** Đại học Đại Nam, Hà Nội, Việt Nam
- **Kaggle notebook:** [link sau khi nộp]
- **GitHub:** [link repository công khai]
- **Demo video:** [link YouTube sau khi nộp]
- **Cloud Run URL:** [link sau khi deploy]
