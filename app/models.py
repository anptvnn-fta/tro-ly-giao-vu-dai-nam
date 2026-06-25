"""
Các Pydantic model dùng trong toàn bộ hệ thống Trợ lý Giáo vụ Đại Nam.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Output schema cho node intake (phân loại yêu cầu)
# ---------------------------------------------------------------------------

class PhanLoaiYeuCau(BaseModel):
    """Schema đầu ra của node intake — phân loại yêu cầu của cán bộ giáo vụ."""

    loai: Literal[
        "tra_cuu_quy_che",
        "lo_trinh_hoc_lai",
        "tra_cuu_lich_diem",
        "sinh_bieu_mau",
        "ngoai_pham_vi",
    ] = Field(
        description=(
            "Loại yêu cầu: "
            "'tra_cuu_quy_che' = hỏi về quy chế/quy định đào tạo; "
            "'lo_trinh_hoc_lai' = lập lộ trình học lại / trả nợ học phần cho sinh viên; "
            "'tra_cuu_lich_diem' = tra cứu lịch học hoặc bảng điểm; "
            "'sinh_bieu_mau' = tạo biểu mẫu theo dõi; "
            "'ngoai_pham_vi' = yêu cầu nằm ngoài phạm vi hỗ trợ."
        )
    )
    ma_sv: Optional[str] = Field(
        default=None,
        description="Mã sinh viên được đề cập trong yêu cầu (nếu có, dạng 8-12 chữ số).",
    )
    do_nhay_cam: Literal["thuong", "nhay_cam"] = Field(
        default="thuong",
        description=(
            "'nhay_cam' nếu yêu cầu liên quan đến dữ liệu cá nhân nhạy cảm "
            "(điểm số chi tiết, học lực, cảnh báo học vụ); 'thuong' cho mọi trường hợp còn lại."
        ),
    )
    cau_hoi_goc: str = Field(
        default="",
        description=(
            "Sao chép NGUYÊN VĂN toàn bộ yêu cầu/câu hỏi gốc của cán bộ. Các node "
            "chuyên môn phía sau (tra cứu quy chế, lịch/điểm, biểu mẫu) dùng trường này "
            "để xử lý đúng nội dung, vì chúng không thấy lại tin nhắn gốc."
        ),
    )


# ---------------------------------------------------------------------------
# Model phản hồi chung của các agent chuyên biệt
# ---------------------------------------------------------------------------

class KetQuaXuLy(BaseModel):
    """Kết quả xử lý cuối cùng trả về sau khi ghi nhật ký."""

    loai_yeu_cau: str
    ma_sv: Optional[str] = None
    noi_dung: str = Field(description="Nội dung trả lời bằng tiếng Việt.")
    can_bo: str = Field(default="he_thong")
    da_ghi_nhat_ky: bool = False
