"""
Cấu hình OpenTelemetry và GenAI telemetry cho Trợ lý Giáo vụ Đại Nam.

Thiết kế an toàn (safe no-op): nếu thư viện GCP không được cài đặt,
hàm setup_telemetry() vẫn chạy thành công mà không ném ngoại lệ.
"""
import logging
import os

logger = logging.getLogger(__name__)


def setup_telemetry() -> str | None:
    """
    Cấu hình OpenTelemetry với GCS upload nếu có bucket được cấu hình.

    Biến môi trường:
    - LOGS_BUCKET_NAME: Tên bucket GCS để lưu trace (ví dụ: my-project-logs).
    - OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT: Bật/tắt ghi nội dung.
      Đặt thành "NO_CONTENT" để chỉ ghi metadata (không ghi nội dung prompt/response).

    Returns:
        Tên bucket nếu đã cấu hình, None nếu không có.
    """
    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
    )

    if bucket and capture_content != "false":
        logger.info(
            "Ghi log prompt/response đã bật — chế độ: NO_CONTENT (chỉ metadata, "
            "không ghi nội dung prompt/response)"
        )
        # Chế độ an toàn: chỉ ghi metadata, không ghi nội dung
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
        )
        commit_sha = os.environ.get("COMMIT_SHA", "dev")
        os.environ.setdefault(
            "OTEL_RESOURCE_ATTRIBUTES",
            f"service.namespace=tro-ly-giao-vu,service.version={commit_sha}",
        )
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )
    else:
        logger.info(
            "Ghi log prompt/response đã tắt. "
            "Đặt LOGS_BUCKET_NAME và OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT để bật."
        )

    # Thử khởi tạo instrumentation GenAI nếu có cài đặt
    try:
        from opentelemetry.instrumentation.google_genai import GoogleGenAIInstrumentor  # type: ignore

        GoogleGenAIInstrumentor().instrument()
        logger.info("OpenTelemetry GoogleGenAI instrumentation đã được kích hoạt.")
    except ImportError:
        logger.debug(
            "opentelemetry-instrumentation-google-genai chưa được cài đặt — bỏ qua instrumentation."
        )
    except Exception as exc:
        logger.warning("Không thể khởi tạo GenAI instrumentation: %s", exc)

    return bucket
