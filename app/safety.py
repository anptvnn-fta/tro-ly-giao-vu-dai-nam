"""
SafetyPlugin cho Trợ lý Giáo vụ Đại Nam.

Triển khai 3 callback bảo mật theo Day 4 (ADK 2.0):
1. before_model_callback  — phát hiện prompt injection (VN + EN).
2. after_model_callback   — che giấu PII trong đầu ra.
3. before_tool_callback   — kiểm tra quyền (RBAC) trước khi gọi tool.

Vai trò và quyền được định nghĩa trong app/tools.py (ROLES + kiem_tra_quyen).
"""
from __future__ import annotations

import re
from typing import Any

from app.tools import ROLES, kiem_tra_quyen

# ---------------------------------------------------------------------------
# Mẫu regex phát hiện prompt injection
# ---------------------------------------------------------------------------

_INJECT_PATTERNS = [
    # Tiếng Việt
    r"bỏ\s*qua",
    r"quên\s*(đi\s+)?(hướng\s+dẫn|chỉ\s+thị|lệnh)",
    r"bỏ\s*qua\s+(hướng\s+dẫn|chỉ\s+thị|lệnh\s+hệ\s+thống)",
    r"thay\s+đổi\s+(vai\s+trò|quyền\s+truy\s+cập)",
    r"hãy\s+(đóng\s+vai|giả\s+vờ\s+là)",
    r"chế\s+độ\s+nhà\s+phát\s+triển",
    r"vô\s+hiệu\s+hóa\s+(kiểm\s+tra|bộ\s+lọc)",
    # Tiếng Anh
    r"ignore\s+(previous|all|system|prior|above)",
    r"forget\s+(your|all|the)\s+(instructions?|prompt|rules?)",
    r"system\s*prompt",
    r"act\s+as\s+(if\s+you\s+are|a\s+)",
    r"developer\s+mode",
    r"jailbreak",
    r"disable\s+(safety|filter|guardrail)",
    r"you\s+are\s+now\s+(a\s+)?(?:different|new|another)",
    r"new\s+instructions?:",
    r"override\s+(your|all)",
    r"pretend\s+(you\s+are|to\s+be)",
]

_INJECT_REGEX = re.compile(
    "|".join(_INJECT_PATTERNS),
    re.IGNORECASE | re.UNICODE,
)

# ---------------------------------------------------------------------------
# Mẫu regex PII cần che giấu trong đầu ra
# ---------------------------------------------------------------------------

# Mã sinh viên: 8-12 chữ số liên tiếp
_PATTERN_MA_SV = re.compile(r"\b(\d{8,12})\b")
# Email
_PATTERN_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"
)
# Số điện thoại Việt Nam (10-11 chữ số, có thể có dấu gạch/khoảng)
_PATTERN_SDT = re.compile(
    r"\b(?:0|\+84)\s*[-.]?\s*(?:\d\s*[-.]?){8,10}\d\b"
)

# ---------------------------------------------------------------------------
# Mapping tool -> hành động cần kiểm tra quyền
# ---------------------------------------------------------------------------

_TOOL_TO_HANH_DONG: dict[str, str] = {
    "tra_cuu_quy_che": "tra_cuu_quy_che",
    "lay_ho_so_sinh_vien": "lay_ho_so_sinh_vien",
    "lay_chuong_trinh_dao_tao": "lay_chuong_trinh_dao_tao",
    "tinh_lo_trinh_hoc_lai": "tinh_lo_trinh_hoc_lai",
    "lay_lich_hoc": "lay_lich_hoc",
    "lay_bang_diem": "lay_bang_diem",
    "tao_bieu_mau": "tao_bieu_mau",
    "ghi_nhat_ky_yeu_cau": "ghi_nhat_ky_yeu_cau",
}


# ---------------------------------------------------------------------------
# Các hàm callback
# ---------------------------------------------------------------------------

def before_model_callback(callback_context, llm_request) -> Any | None:
    """
    Kiểm tra prompt injection trước khi gửi đến mô hình ngôn ngữ.

    Nếu phát hiện mẫu injection, trả về phản hồi từ chối bằng tiếng Việt
    thay vì chuyển tiếp yêu cầu đến LLM.

    Args:
        callback_context: Context của ADK (chứa state, agent_name...).
        llm_request: Yêu cầu chuẩn bị gửi đến LLM.

    Returns:
        LlmResponse từ chối nếu phát hiện injection; None nếu bình thường.
    """
    try:
        from google.adk.models import LlmResponse
        from google.genai import types as genai_types
    except ImportError:
        return None

    # Thu thập nội dung text từ tất cả các phần của request
    van_ban_kiem_tra = ""
    if hasattr(llm_request, "contents"):
        for content in llm_request.contents or []:
            for part in getattr(content, "parts", []) or []:
                if hasattr(part, "text") and part.text:
                    van_ban_kiem_tra += " " + part.text

    if _INJECT_REGEX.search(van_ban_kiem_tra):
        tu_choi_msg = (
            "Yêu cầu của bạn chứa nội dung không được phép (có thể là nỗ lực "
            "thay đổi chỉ thị hệ thống). Hệ thống từ chối xử lý yêu cầu này. "
            "Vui lòng đặt câu hỏi bình thường về nghiệp vụ giáo vụ."
        )
        return LlmResponse(
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part.from_text(text=tu_choi_msg)],
            )
        )

    return None


def after_model_callback(callback_context, llm_response) -> Any | None:
    """
    Che giấu PII (mã SV, email, số điện thoại) trong phản hồi của mô hình.

    Chỉ che giấu nếu vai trò hiện tại không phải 'truong_phong_dao_tao'.
    Cán bộ trưởng phòng được xem dữ liệu đầy đủ.

    Args:
        callback_context: Context của ADK.
        llm_response: Phản hồi từ LLM.

    Returns:
        LlmResponse đã che giấu PII nếu cần; None nếu không thay đổi.
    """
    try:
        from google.adk.models import LlmResponse
        from google.genai import types as genai_types
    except ImportError:
        return None

    # Lấy vai trò từ session state
    vai_tro = "giao_vu"
    try:
        state = callback_context.state if hasattr(callback_context, "state") else {}
        vai_tro = state.get("vai_tro", "giao_vu")
    except Exception:
        pass

    # Cán bộ giáo vụ và trưởng phòng được xem dữ liệu đầy đủ (họ cần mã SV để
    # tác nghiệp). Chỉ che PII cho vai trò tra cứu chung / không xác định.
    if vai_tro in ("giao_vu", "truong_phong_dao_tao"):
        return None

    if llm_response is None or not hasattr(llm_response, "content"):
        return None

    content = llm_response.content
    if content is None:
        return None

    da_thay_doi = False
    new_parts = []
    for part in getattr(content, "parts", []) or []:
        if hasattr(part, "text") and part.text:
            van_ban = part.text
            van_ban_moi = van_ban

            # Che giấu mã sinh viên (giữ 4 chữ số đầu, che phần còn lại)
            def _che_ma_sv(m: re.Match) -> str:
                ma = m.group(1)
                return ma[:4] + "*" * (len(ma) - 4)

            van_ban_moi = _PATTERN_MA_SV.sub(_che_ma_sv, van_ban_moi)

            # Che giấu email
            van_ban_moi = _PATTERN_EMAIL.sub("[email đã ẩn]", van_ban_moi)

            # Che giấu số điện thoại
            van_ban_moi = _PATTERN_SDT.sub("[SĐT đã ẩn]", van_ban_moi)

            if van_ban_moi != van_ban:
                da_thay_doi = True

            new_parts.append(genai_types.Part.from_text(text=van_ban_moi))
        else:
            new_parts.append(part)

    if not da_thay_doi:
        return None

    return LlmResponse(
        content=genai_types.Content(role="model", parts=new_parts)
    )


def before_tool_callback(tool, args, tool_context) -> dict | None:
    """
    Kiểm tra quyền trước khi thực thi tool (RBAC deterministic guardrail).

    Lấy vai_tro từ session state, kiểm tra với kiem_tra_quyen().
    Nếu bị từ chối, trả về dict lỗi bằng tiếng Việt thay vì gọi tool.
    Đồng thời validate định dạng mã sinh viên nếu tool nhận tham số ma_sv.

    Args:
        tool: Tool đang được gọi.
        args: Tham số của tool.
        tool_context: ADK ToolContext.

    Returns:
        dict từ chối (thay thế kết quả tool) nếu không có quyền;
        None nếu được phép (ADK sẽ tiếp tục gọi tool thật).
    """
    ten_tool = getattr(tool, "name", None) or getattr(tool, "__name__", "unknown")

    # Lấy vai trò từ session state (mặc định 'giao_vu' — người dùng chính)
    vai_tro = "giao_vu"
    try:
        state = tool_context.state if hasattr(tool_context, "state") else {}
        vai_tro = state.get("vai_tro", "giao_vu")
    except Exception:
        pass

    # Xác định hành động cần kiểm tra
    hanh_dong = _TOOL_TO_HANH_DONG.get(ten_tool, ten_tool)

    # Kiểm tra quyền
    if not kiem_tra_quyen(vai_tro, hanh_dong):
        quyen_hien_co = ROLES.get(vai_tro, [])
        return {
            "loi": (
                f"Bạn không có quyền thực hiện '{hanh_dong}'. "
                f"Vai trò '{vai_tro}' chỉ được phép: {', '.join(quyen_hien_co) or 'không có quyền nào'}."
            ),
            "tu_choi": True,
            "vai_tro": vai_tro,
            "hanh_dong_yeu_cau": hanh_dong,
        }

    # Validate mã sinh viên nếu có
    ma_sv = args.get("ma_sv", "")
    if ma_sv and not re.match(r"^\d{8,12}$", str(ma_sv).strip()):
        return {
            "loi": (
                f"Mã sinh viên '{ma_sv}' không hợp lệ. "
                "Mã sinh viên phải gồm 8-12 chữ số (ví dụ: 20001234)."
            ),
            "tu_choi": False,
        }

    return None  # Cho phép gọi tool


# ---------------------------------------------------------------------------
# SafetyPlugin class (tích hợp vào ADK App nếu SDK hỗ trợ plugin interface)
# ---------------------------------------------------------------------------

class SafetyPlugin:
    """
    Plugin bảo mật tổng hợp cho Trợ lý Giáo vụ Đại Nam.

    Đăng ký 3 callback:
    - before_model_callback: phát hiện prompt injection.
    - after_model_callback: che giấu PII.
    - before_tool_callback: kiểm tra RBAC.
    """

    def before_model_callback(self, callback_context, llm_request):
        return before_model_callback(callback_context, llm_request)

    def after_model_callback(self, callback_context, llm_response):
        return after_model_callback(callback_context, llm_response)

    def before_tool_callback(self, tool, args, tool_context):
        return before_tool_callback(tool, args, tool_context)
