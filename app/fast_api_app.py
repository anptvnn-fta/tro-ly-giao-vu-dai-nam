"""
FastAPI application cho Trợ lý Giáo vụ Đại Nam.

Endpoint chính: ADK FastAPI app (get_fast_api_app) với tiêu đề "tro-ly-giao-vu".
Endpoint phụ: POST /feedback — thu thập đánh giá chất lượng từ cán bộ giáo vụ.
"""
import csv
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from pydantic import BaseModel

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Khởi tạo telemetry (safe no-op nếu GCP libs không có)
# ---------------------------------------------------------------------------
setup_telemetry()

# ---------------------------------------------------------------------------
# Khởi tạo Google Cloud Logging (tùy chọn — bỏ qua nếu không có GCP)
# ---------------------------------------------------------------------------
_cloud_logger = None
try:
    import google.auth
    from google.cloud import logging as google_cloud_logging

    _, project_id = google.auth.default()
    logging_client = google_cloud_logging.Client()
    _cloud_logger = logging_client.logger(__name__)
    logger.info("Google Cloud Logging đã được kích hoạt (project: %s).", project_id)
except Exception as exc:
    logger.info("Google Cloud Logging không khả dụng (%s) — dùng logging chuẩn.", exc)

# ---------------------------------------------------------------------------
# Cấu hình
# ---------------------------------------------------------------------------
allow_origins_raw = os.getenv("ALLOW_ORIGINS", "")
allow_origins = allow_origins_raw.split(",") if allow_origins_raw else None

logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None
session_service_uri = None  # In-memory session (stateless container)

# Thư mục chứa app/ (project root)
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Chỉ xuất telemetry lên Google Cloud khi có dự án/credentials GCP. Khi chạy
# local chỉ với Google AI Studio API key, bật cờ này sẽ gây lỗi
# google.auth.default() (DefaultCredentialsError) -> mặc định TẮT.
_otel_to_cloud = bool(
    os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("LOGS_BUCKET_NAME")
)

# ---------------------------------------------------------------------------
# Tạo FastAPI app từ ADK
# ---------------------------------------------------------------------------
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=_otel_to_cloud,
)

app.title = "tro-ly-giao-vu"
app.description = (
    "API cho Trợ lý Giáo vụ số Đại Nam — hỗ trợ cán bộ giáo vụ tra cứu quy chế, "
    "lập lộ trình học lại, tra cứu lịch & điểm, tạo biểu mẫu theo dõi."
)
app.version = "1.0.0"


# ---------------------------------------------------------------------------
# Endpoint thu thập phản hồi (Agent Quality Flywheel — Day 4)
# ---------------------------------------------------------------------------

@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """
    Thu thập và ghi lại phản hồi chất lượng từ cán bộ giáo vụ.

    Phản hồi này được dùng để cải thiện chất lượng agent theo chu trình
    HITL feedback -> eval cases mới -> tối ưu prompt (Agent Quality Flywheel).

    Args:
        feedback: Dữ liệu phản hồi (điểm, nhận xét, loại yêu cầu).

    Returns:
        Dict xác nhận thành công.
    """
    feedback_data = feedback.model_dump()

    if _cloud_logger is not None:
        try:
            _cloud_logger.log_struct(feedback_data, severity="INFO")
        except Exception as exc:
            logger.warning("Không thể ghi Cloud Logging: %s", exc)

    logger.info("Phản hồi nhận được: %s", feedback_data)
    return {"status": "success", "thong_bao": "Cảm ơn phản hồi của bạn!"}


# ---------------------------------------------------------------------------
# Endpoint /chat — cầu nối đơn giản cho dashboard Flask
# ---------------------------------------------------------------------------
# ADK cung cấp sẵn /run nhưng yêu cầu schema phức tạp (app_name, user_id,
# session_id, new_message). Endpoint /chat này nhận {message, session_state}
# từ frontend, tạo session kèm vai_tro rồi chạy agent, trả về {"response": ...}.


class ChatRequest(BaseModel):
    """Yêu cầu chat từ dashboard giáo vụ."""

    message: str
    session_state: dict | None = None


_NHAT_KY_FILE = Path(__file__).resolve().parent.parent / "data" / "nhat_ky_yeu_cau.csv"


def _ghi_nhat_ky(loai_yeu_cau: str, ma_sv: str, vai_tro: str, tom_tat: str) -> None:
    """Ghi 1 dòng nhật ký yêu cầu (nguồn cho trang Báo cáo xử lý yêu cầu)."""
    header = ["thoi_gian", "can_bo", "vai_tro", "loai_yeu_cau", "ma_sv", "ket_qua_tom_tat"]
    row = {
        "thoi_gian": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "can_bo": "can_bo_giao_vu",
        "vai_tro": vai_tro,
        "loai_yeu_cau": loai_yeu_cau or "khac",
        "ma_sv": ma_sv or "",
        "ket_qua_tom_tat": (tom_tat or "")[:180],
    }
    ton_tai = _NHAT_KY_FILE.exists() and _NHAT_KY_FILE.stat().st_size > 0
    with open(_NHAT_KY_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if not ton_tai:
            w.writeheader()
        w.writerow(row)


# Runner được khởi tạo lười (lazy) để lỗi import không làm sập toàn app.
_giaovu_runner = None


def _lay_runner():
    global _giaovu_runner
    if _giaovu_runner is None:
        from google.adk.runners import InMemoryRunner

        from app.agent import root_agent

        _giaovu_runner = InMemoryRunner(agent=root_agent, app_name="tro-ly-giao-vu")
    return _giaovu_runner


@app.post("/chat")
async def chat(req: ChatRequest) -> dict:
    """Chạy agent giáo vụ cho một tin nhắn, gắn vai_tro vào session state.

    Args:
        req: {message, session_state: {"vai_tro": ...}}

    Returns:
        {"response": "<văn bản trả lời>"} hoặc {"response": "", "error": "..."}
    """
    from google.genai import types as genai_types

    vai_tro = (req.session_state or {}).get("vai_tro", "giao_vu")
    user_id = "can_bo_giao_vu"
    try:
        runner = _lay_runner()
        session = await runner.session_service.create_session(
            app_name="tro-ly-giao-vu",
            user_id=user_id,
            state={"vai_tro": vai_tro},
        )
        new_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=req.message)],
        )
        final_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=new_message,
        ):
            content = getattr(event, "content", None)
            for part in (getattr(content, "parts", None) or []):
                if getattr(part, "text", None):
                    final_text = part.text

        # Ghi nhật ký yêu cầu cho trang Báo cáo (đọc phân loại từ session state).
        # Lỗi ghi log không được làm hỏng phản hồi.
        try:
            sess = await runner.session_service.get_session(
                app_name="tro-ly-giao-vu", user_id=user_id, session_id=session.id
            )
            state = getattr(sess, "state", {}) or {}
            phan_loai = state.get("phan_loai") or {}
            if not isinstance(phan_loai, dict):
                phan_loai = {}
            _ghi_nhat_ky(
                loai_yeu_cau=phan_loai.get("loai", "khac"),
                ma_sv=phan_loai.get("ma_sv") or "",
                vai_tro=vai_tro,
                tom_tat=final_text,
            )
        except Exception:
            logger.debug("Bỏ qua ghi nhật ký /chat", exc_info=True)

        return {"response": final_text or "(Không có nội dung phản hồi)", "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Lỗi khi xử lý /chat")
        return {"response": "", "error": f"Lỗi khi gọi agent: {exc}"}


# ---------------------------------------------------------------------------
# Chạy trực tiếp (phát triển local)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
