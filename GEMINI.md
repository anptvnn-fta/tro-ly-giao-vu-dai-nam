# Hướng dẫn phát triển — Trợ lý Giáo vụ Đại Nam

Dự án: **TroLyGiaoVu** — Trợ lý Giáo vụ số, ADK 2.0 + Gemini Flash  
Chủ nhiệm: Phạm Thế An (anpt@dainam.edu.vn), Đại học Đại Nam  
Kaggle Track: "Agents for Good" — Deadline 2026-07-06

---

## Cài đặt (Prerequisites)

```bash
# Cài agents-cli (một lần duy nhất)
uv tool install google-agents-cli

# Cài dependencies dự án
cd Capstone_GiaoVu_DaiNam
uv pip install -e .

# Sao chép biến môi trường
cp .env.example .env
# Điền GOOGLE_API_KEY hoặc GOOGLE_CLOUD_PROJECT vào .env
```

---

## Cấu trúc thư mục

```
Capstone_GiaoVu_DaiNam/
├── app/
│   ├── __init__.py          # Export app
│   ├── agent.py             # ADK Workflow: intake -> route -> chuyên gia -> merge_log
│   ├── tools.py             # 8 tools + kiem_tra_quyen + ROLES
│   ├── safety.py            # SafetyPlugin: injection, PII, RBAC
│   ├── models.py            # Pydantic schemas (PhanLoaiYeuCau...)
│   ├── fast_api_app.py      # FastAPI app + /feedback endpoint
│   └── app_utils/
│       ├── typing.py        # Feedback model
│       └── telemetry.py     # OpenTelemetry setup (safe no-op)
├── data/
│   ├── quy_che/             # Tài liệu quy chế (.md)
│   ├── chuong_trinh_dao_tao.json
│   ├── sinh_vien_diem.csv
│   ├── lich_hoc.csv
│   └── nhat_ky_yeu_cau.csv  # Nhật ký yêu cầu (tự ghi)
├── tests/eval/
│   ├── datasets/giaovu-dataset.json   # 20 eval cases
│   └── eval_config.yaml
├── frontend/                # Flask dashboard (dark theme)
├── pyproject.toml
├── agents-cli-manifest.yaml
├── Procfile
├── Dockerfile
└── .env.example
```

---

## Luồng xử lý Agent (ADK Workflow)

```
Yêu cầu cán bộ giáo vụ
    |
    v
[intake] — Phân loại yêu cầu (PhanLoaiYeuCau)
    |
    v
[route_intake] — Định tuyến theo loai
    |
    +--tra_cuu_quy_che  --> [reg_lookup]   (tra_cuu_quy_che tool, RAG đơn giản)
    +--lo_trinh_hoc_lai --> [path_planner] (tinh_lo_trinh_hoc_lai, topo-sort)
    +--tra_cuu_lich_diem--> [lich_diem]    (lay_lich_hoc, lay_bang_diem)
    +--sinh_bieu_mau    --> [form_filler]  (tao_bieu_mau)
    +--ngoai_pham_vi    --> [escalate]     (HITL queue)
    |
    v
[merge_log] — Ghi nhật ký + trả kết quả cuối
```

---

## Vai trò và Phân quyền (RBAC)

| Vai trò | Quyền |
|---------|-------|
| `tra_cuu_vien` | Chỉ tra cứu quy chế |
| `giao_vu` | Tra cứu + lộ trình + lịch/điểm + biểu mẫu + nhật ký |
| `truong_phong_dao_tao` | Toàn quyền + duyệt HITL + xem PII đầy đủ |

Vai trò được truyền qua session state key `vai_tro`.

---

## Lệnh phát triển

| Lệnh | Mục đích |
|------|---------|
| `agents-cli playground` | Chạy interactive local |
| `uv run uvicorn app.fast_api_app:app --reload` | Chạy FastAPI dev server |
| `uv run pytest tests/` | Chạy tất cả tests |
| `agents-cli eval generate` | Chạy agent trên eval dataset |
| `agents-cli eval grade` | Chấm điểm kết quả eval |
| `agents-cli eval compare` | So sánh hai lần eval (regression check) |
| `agents-cli lint` | Kiểm tra chất lượng code |
| `agents-cli deploy` | Deploy lên Cloud Run (cần xác nhận) |

---

## Quy tắc phát triển (quan trọng)

- **KHÔNG thay đổi model** trừ khi được yêu cầu. Model hiện tại: `gemini-flash-latest`.
- **KHÔNG commit file .env** hoặc dữ liệu sinh viên thật.
- **Luôn dùng `uv run`** khi chạy Python: `uv run python script.py`.
- **Lỗi 404 model**: sửa `GOOGLE_CLOUD_LOCATION` (thử `global`), không sửa tên model.
- **Tất cả text người dùng bằng tiếng Việt** — không dùng tiếng Anh trong response.
- **Dữ liệu mẫu** (data/*.csv, data/*.json) là dữ liệu giả lập cho pilot — không dùng dữ liệu sinh viên thật.

---

## Các khái niệm ADK được minh họa

| Tính năng ADK | Node/File |
|--------------|-----------|
| LlmAgent + output_schema | `intake` (PhanLoaiYeuCau) |
| Workflow + routing | `route_intake` (Event + route) |
| Function tools + ToolContext | `tools.py` (8 tools) |
| before_model_callback (injection) | `safety.py` |
| after_model_callback (PII redact) | `safety.py` |
| before_tool_callback (RBAC) | `safety.py` |
| Session state scratchpad | `output_key=` trên mỗi LlmAgent |
| HITL escalation | `escalate()` node |
| FastAPI + Cloud Run deploy | `fast_api_app.py` + `Dockerfile` |
| ADK Eval + Quality Flywheel | `tests/eval/` + `/feedback` endpoint |

---

## Liên hệ

- Chủ nhiệm: Phạm Thế An — anpt@dainam.edu.vn  
- Trường Đại học Đại Nam, Hà Nội, Việt Nam
