"""
Các kiểu dữ liệu dùng chung cho Trợ lý Giáo vụ Đại Nam.
"""
import uuid
from typing import Literal

from pydantic import BaseModel, Field


class Feedback(BaseModel):
    """Phản hồi chất lượng từ cán bộ giáo vụ về kết quả xử lý yêu cầu."""

    score: int | float = Field(
        description="Điểm đánh giá từ 1 (kém) đến 5 (xuất sắc)."
    )
    text: str | None = Field(
        default="",
        description="Nhận xét tự do (tùy chọn).",
    )
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["tro-ly-giao-vu"] = "tro-ly-giao-vu"
    user_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID ẩn danh của người dùng.",
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID phiên làm việc.",
    )
    loai_yeu_cau: str | None = Field(
        default=None,
        description="Loại yêu cầu liên quan đến phản hồi này.",
    )
