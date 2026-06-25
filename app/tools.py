"""
Các công cụ (tools) cho Trợ lý Giáo vụ Đại Nam.

Mỗi tool đều có:
- Docstring tiếng Việt mô tả mục đích, tham số, giá trị trả về.
- ToolContext để truy cập session state (vai trò, mã SV).
- Xử lý lỗi an toàn, trả về dict nhất quán.

Dữ liệu được đọc từ thư mục data/ nằm ở project root (Capstone_GiaoVu_DaiNam/).
"""
from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Đường dẫn dữ liệu
# ---------------------------------------------------------------------------

# Project root = thư mục chứa file này (app/) lùi lên một cấp
_PROJECT_ROOT = Path(__file__).parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_QUY_CHE_DIR = _DATA_DIR / "quy_che"
_CDT_FILE = _DATA_DIR / "chuong_trinh_dao_tao.json"
_SV_DIEM_FILE = _DATA_DIR / "sinh_vien_diem.csv"
_LICH_HOC_FILE = _DATA_DIR / "lich_hoc.csv"
_NHAT_KY_FILE = _DATA_DIR / "nhat_ky_yeu_cau.csv"


# ---------------------------------------------------------------------------
# Kiểm tra quyền (role gate) — dùng cả bên safety.py
# ---------------------------------------------------------------------------

# Định nghĩa quyền theo vai trò:
#   giao_vu            : tra cứu quy chế + lập lộ trình + tạo biểu mẫu (KHÔNG xem dữ liệu ngoài phạm vi)
#   truong_phong_dao_tao: toàn quyền kể cả duyệt HITL và xem dữ liệu nhạy cảm
#   tra_cuu_vien       : CHỈ tra cứu quy chế
# Các hành động NHẠY CẢM: chỉ trưởng phòng đào tạo mới được phép.
HANH_DONG_NHAY_CAM: set[str] = {
    "duyet_hitl",            # Duyệt yêu cầu HITL trong hàng đợi
    "xem_du_lieu_nhay_cam",  # Xem dữ liệu cá nhân không bị che
    "xuat_bao_cao",          # Xuất báo cáo tổng hợp xử lý yêu cầu
}

ROLES: dict[str, list[str]] = {
    "truong_phong_dao_tao": [
        "tra_cuu_quy_che",
        "lay_ho_so_sinh_vien",
        "lay_chuong_trinh_dao_tao",
        "tinh_lo_trinh_hoc_lai",
        "lay_lich_hoc",
        "lay_bang_diem",
        "tao_bieu_mau",
        "ghi_nhat_ky_yeu_cau",
        # Quyền nhạy cảm (chỉ trưởng phòng):
        "duyet_hitl",
        "xem_du_lieu_nhay_cam",
        "xuat_bao_cao",
    ],
    "giao_vu": [
        "tra_cuu_quy_che",
        "lay_ho_so_sinh_vien",
        "lay_chuong_trinh_dao_tao",
        "tinh_lo_trinh_hoc_lai",
        "lay_lich_hoc",
        "lay_bang_diem",
        "tao_bieu_mau",
        "ghi_nhat_ky_yeu_cau",
    ],
    "tra_cuu_vien": [
        "tra_cuu_quy_che",
    ],
}


def kiem_tra_quyen(vai_tro: str, hanh_dong: str) -> bool:
    """
    Kiểm tra vai trò có được phép thực hiện hành động không.

    Args:
        vai_tro: Vai trò của người dùng ('giao_vu', 'truong_phong_dao_tao', 'tra_cuu_vien').
        hanh_dong: Hành động cần kiểm tra (tên tool hoặc quyền cụ thể).

    Returns:
        True nếu được phép, False nếu bị từ chối.
    """
    danh_sach_quyen = ROLES.get(vai_tro, [])
    return hanh_dong in danh_sach_quyen


# ---------------------------------------------------------------------------
# Helper nội bộ
# ---------------------------------------------------------------------------

def _doc_csv(duong_dan: Path) -> list[dict[str, str]]:
    """Đọc file CSV, trả về list dict. Trả về [] nếu file không tồn tại."""
    if not duong_dan.exists():
        return []
    with open(duong_dan, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def _doc_json(duong_dan: Path) -> Any:
    """Đọc file JSON. Trả về None nếu không tồn tại."""
    if not duong_dan.exists():
        return None
    with open(duong_dan, encoding="utf-8") as f:
        return json.load(f)


def _so_an_toan(gia_tri: Any, kieu, mac_dinh):
    """Ép kiểu số an toàn (xử lý ô rỗng trong CSV). Trả về mac_dinh nếu lỗi."""
    try:
        chuoi = str(gia_tri).strip()
        if chuoi == "":
            return mac_dinh
        return kieu(float(chuoi)) if kieu is int else kieu(chuoi)
    except (TypeError, ValueError):
        return mac_dinh


def _vai_tro_tu_context(tool_context) -> str:
    """Lấy vai_tro từ session state của ToolContext. Mặc định 'giao_vu'.

    'giao_vu' (cán bộ giáo vụ) là người dùng chính theo phiếu yêu cầu, nên là
    mặc định hợp lý khi chạy thử ở ADK playground (chưa đặt state).
    """
    if tool_context is None:
        return "giao_vu"
    try:
        state = tool_context.state if hasattr(tool_context, "state") else {}
        return (state or {}).get("vai_tro", "giao_vu")
    except Exception:
        return "giao_vu"


# ---------------------------------------------------------------------------
# 1. Tra cứu quy chế
# ---------------------------------------------------------------------------

def tra_cuu_quy_che(cau_hoi: str, tool_context=None) -> dict:
    """
    Tìm kiếm đoạn văn bản liên quan trong tài liệu quy chế đào tạo.

    Thực hiện tìm kiếm dựa trên từ khóa và độ trùng lặp token giữa câu hỏi
    và các đoạn văn trong file markdown quy chế.

    Args:
        cau_hoi: Câu hỏi hoặc từ khóa cần tra cứu bằng tiếng Việt.
        tool_context: ADK ToolContext (không bắt buộc).

    Returns:
        dict với các trường:
        - doan_van: list[str] — các đoạn văn phù hợp nhất (tối đa 5 đoạn).
        - nguon: list[dict] — danh sách nguồn trích dẫn {tep, dieu, khoan}.
        - tim_thay: bool — có tìm thấy kết quả không.
    """
    if not _QUY_CHE_DIR.exists():
        return {"doan_van": [], "nguon": [], "tim_thay": False,
                "loi": "Thư mục quy chế không tồn tại."}

    # Chuẩn hóa câu hỏi thành set token
    tokens_hoi = set(re.findall(r"\w+", cau_hoi.lower()))

    ket_qua: list[tuple[float, str, str, str, str]] = []  # (score, doan, tep, dieu, khoan)

    for md_file in sorted(_QUY_CHE_DIR.glob("*.md")):
        with open(md_file, encoding="utf-8") as f:
            noi_dung = f.read()

        dieu_hien_tai = ""
        khoan_hien_tai = ""

        # Tách thành đoạn theo dòng trống
        doan_list = [d.strip() for d in re.split(r"\n{2,}", noi_dung) if d.strip()]
        for doan in doan_list:
            # Theo dõi Điều và Khoản
            m_dieu = re.search(r"(Điều\s+\d+[^:\n]*)", doan)
            m_khoan = re.search(r"(Khoản\s+\d+[^:\n]*)", doan)
            if m_dieu:
                dieu_hien_tai = m_dieu.group(1).strip()
            if m_khoan:
                khoan_hien_tai = m_khoan.group(1).strip()

            tokens_doan = set(re.findall(r"\w+", doan.lower()))
            if not tokens_doan:
                continue

            # Jaccard overlap
            giao = tokens_hoi & tokens_doan
            hop = tokens_hoi | tokens_doan
            score = len(giao) / len(hop) if hop else 0.0

            if score > 0.05 or any(t in doan.lower() for t in tokens_hoi if len(t) > 3):
                # Tăng điểm nếu có từ dài trùng khớp
                bonus = sum(1 for t in tokens_hoi if len(t) > 3 and t in doan.lower())
                ket_qua.append((score + bonus * 0.1, doan[:500], md_file.name, dieu_hien_tai, khoan_hien_tai))

    # Sắp xếp theo điểm, lấy top 5
    ket_qua.sort(key=lambda x: x[0], reverse=True)
    top5 = ket_qua[:5]

    if not top5:
        return {"doan_van": [], "nguon": [], "tim_thay": False}

    doan_van = [x[1] for x in top5]
    nguon = [
        {"tep": x[2], "dieu": x[3], "khoan": x[4]}
        for x in top5
    ]
    return {"doan_van": doan_van, "nguon": nguon, "tim_thay": True}


# ---------------------------------------------------------------------------
# 2. Lấy hồ sơ sinh viên (điểm số)
# ---------------------------------------------------------------------------

def lay_ho_so_sinh_vien(ma_sv: str, tool_context=None) -> dict:
    """
    Lấy hồ sơ và bảng điểm của một sinh viên từ file dữ liệu.

    Args:
        ma_sv: Mã sinh viên (8-12 chữ số).
        tool_context: ADK ToolContext.

    Returns:
        dict với các trường:
        - ma_sv: Mã sinh viên.
        - ho_ten: Họ tên sinh viên.
        - nganh: Ngành học.
        - bang_diem: list[dict] — danh sách môn học và điểm.
        - mon_truot_no: list[dict] — các môn trượt hoặc nợ.
        - tim_thay: bool.
    """
    # Tự kiểm tra quyền (phòng thủ theo chiều sâu — Day 4).
    # Mọi truy cập dữ liệu cá nhân SV (điểm/lịch/lộ trình) đều đi qua hàm này.
    vai_tro = _vai_tro_tu_context(tool_context)
    if not kiem_tra_quyen(vai_tro, "lay_ho_so_sinh_vien"):
        return {
            "tim_thay": False,
            "tu_choi": True,
            "loi": (
                f"Vai trò '{vai_tro}' không có quyền truy cập hồ sơ/điểm sinh viên. "
                "Chỉ cán bộ giáo vụ hoặc trưởng phòng đào tạo mới được phép."
            ),
        }

    if not re.match(r"^\d{8,12}$", ma_sv.strip()):
        return {"loi": f"Mã sinh viên '{ma_sv}' không hợp lệ (cần 8-12 chữ số).", "tim_thay": False}

    rows = _doc_csv(_SV_DIEM_FILE)
    rows_sv = [r for r in rows if r.get("ma_sv", "").strip() == ma_sv.strip()]

    if not rows_sv:
        return {"ma_sv": ma_sv, "tim_thay": False, "loi": f"Không tìm thấy sinh viên có mã '{ma_sv}'."}

    ho_ten = rows_sv[0].get("ho_ten", "")
    nganh = rows_sv[0].get("nganh", "")

    bang_diem = []
    for r in rows_sv:
        mon = {
            "ma_mon": (r.get("ma_mon", "") or "").strip(),
            "ten_mon": (r.get("ten_mon", "") or "").strip(),
            "tin_chi": _so_an_toan(r.get("tin_chi"), int, 3),
            "diem_chu": (r.get("diem_chu", "") or "").strip(),
            "diem_so": _so_an_toan(r.get("diem_so"), float, 0.0),
            "ky": (r.get("ky", "") or "").strip(),
            "trang_thai": (r.get("trang_thai", "") or "").strip().lower(),
        }
        bang_diem.append(mon)

    # Tập môn đã từng ĐẠT (dù học lại nhiều lần) -> không tính là còn nợ nữa.
    ma_da_dat = {m["ma_mon"] for m in bang_diem if m["trang_thai"] == "dat"}

    # Môn CÒN NỢ: có ít nhất 1 lần trượt/nợ VÀ chưa có lần nào đạt.
    # Giữ bản ghi MỚI NHẤT (theo thứ tự xuất hiện) cho mỗi mã môn.
    mon_truot_no_map: dict[str, dict] = {}
    for m in bang_diem:
        if m["trang_thai"] in ("truot", "no") and m["ma_mon"] not in ma_da_dat:
            mon_truot_no_map[m["ma_mon"]] = m  # ghi đè -> giữ bản ghi sau cùng
    mon_truot_no = list(mon_truot_no_map.values())

    return {
        "ma_sv": ma_sv,
        "ho_ten": ho_ten,
        "nganh": nganh,
        "bang_diem": bang_diem,
        "mon_truot_no": mon_truot_no,
        "tim_thay": True,
    }


# ---------------------------------------------------------------------------
# 3. Lấy chương trình đào tạo
# ---------------------------------------------------------------------------

def lay_chuong_trinh_dao_tao(nganh: str, tool_context=None) -> dict:
    """
    Lấy chương trình đào tạo (danh sách môn học, tiên quyết, tín chỉ) theo ngành.

    Hỗ trợ cả hai định dạng JSON:
    1. Dict keyed by ngành: {"CNTT": [...], "KT": [...]}
    2. Object đơn: {"nganh": "CNTT", "hoc_phan": [...]} hoặc {"nganh": "CNTT", "mon_hoc": [...]}

    Args:
        nganh: Tên ngành học (ví dụ: 'CNTT', 'Kế toán').
        tool_context: ADK ToolContext.

    Returns:
        dict với các trường:
        - nganh: Tên ngành.
        - mon_hoc: list[dict] — danh sách môn học với ma_mon, ten_mon, tin_chi, tien_quyet, ky_goi_y.
        - tim_thay: bool.
    """
    data = _doc_json(_CDT_FILE)
    if data is None:
        return {"loi": "Không tải được file chương trình đào tạo.", "tim_thay": False}

    # Định dạng 2: object đơn với key "nganh" hoặc "ten_nganh"
    if isinstance(data, dict) and ("nganh" in data or "ten_nganh" in data):
        ten_nganh = data.get("nganh", data.get("ten_nganh", ""))
        # Kiểm tra có phải ngành cần tìm không
        phu_hop = (
            ten_nganh.lower() == nganh.lower()
            or nganh.lower() in ten_nganh.lower()
            or ten_nganh.lower() in nganh.lower()
        )
        if phu_hop:
            # Lấy danh sách môn (thử các key phổ biến)
            mon_hoc = data.get("mon_hoc") or data.get("hoc_phan") or []
            # Chuẩn hóa: đảm bảo mỗi môn có trường tien_quyet
            mon_hoc_chuan = []
            for m in mon_hoc:
                mon_hoc_chuan.append({
                    "ma_mon": m.get("ma_mon", ""),
                    "ten_mon": m.get("ten_mon", ""),
                    "tin_chi": m.get("tin_chi", 3),
                    "tien_quyet": m.get("tien_quyet", []),
                    "ky_goi_y": m.get("ky_goi_y", 1),
                })
            return {"nganh": ten_nganh, "mon_hoc": mon_hoc_chuan, "tim_thay": True}
        else:
            return {
                "nganh": nganh,
                "tim_thay": False,
                "loi": f"File chương trình đào tạo chứa ngành '{ten_nganh}', "
                       f"không phải ngành '{nganh}'.",
            }

    # Định dạng 1: dict keyed by ngành
    if isinstance(data, dict):
        nganh_key = None
        for k in data:
            if k.lower() == nganh.lower() or nganh.lower() in k.lower():
                nganh_key = k
                break

        if nganh_key is None:
            return {
                "nganh": nganh,
                "tim_thay": False,
                "loi": f"Không tìm thấy chương trình đào tạo cho ngành '{nganh}'. "
                       f"Các ngành hiện có: {', '.join(data.keys())}",
            }

        mon_hoc_raw = data[nganh_key]
        mon_hoc_chuan = []
        for m in (mon_hoc_raw if isinstance(mon_hoc_raw, list) else []):
            mon_hoc_chuan.append({
                "ma_mon": m.get("ma_mon", ""),
                "ten_mon": m.get("ten_mon", ""),
                "tin_chi": m.get("tin_chi", 3),
                "tien_quyet": m.get("tien_quyet", []),
                "ky_goi_y": m.get("ky_goi_y", 1),
            })
        return {"nganh": nganh_key, "mon_hoc": mon_hoc_chuan, "tim_thay": True}

    return {"loi": "Định dạng file chương trình đào tạo không hợp lệ.", "tim_thay": False}


# ---------------------------------------------------------------------------
# 4. Tính lộ trình học lại (CORE ALGORITHM)
# ---------------------------------------------------------------------------

def tinh_lo_trinh_hoc_lai(
    ma_sv: str,
    so_tin_chi_toi_da_moi_ky: int = 18,
    tool_context=None,
) -> dict:
    """
    Tính lộ trình học lại / trả nợ học phần cho sinh viên.

    Thuật toán:
    1. Lấy danh sách môn trượt/nợ của sinh viên.
    2. Lấy chương trình đào tạo để biết tiên quyết.
    3. Topo-sort các môn theo quan hệ tiên quyết.
    4. Xếp lịch học lại theo kỳ với giới hạn tín chỉ tối đa mỗi kỳ.
    5. Kiểm tra xung đột lịch học dùng data/lich_hoc.csv.
    6. Cảnh báo nếu có tiên quyết chưa hoàn thành hoặc trùng lịch.

    Args:
        ma_sv: Mã sinh viên cần lập lộ trình.
        so_tin_chi_toi_da_moi_ky: Số tín chỉ tối đa được đăng ký mỗi kỳ (mặc định 18).
        tool_context: ADK ToolContext.

    Returns:
        dict với:
        - ma_sv, ho_ten, nganh
        - lo_trinh: list[dict] — mỗi phần tử là {ky_hoc_lai, mon_hoc: list, tong_tin_chi}
        - canh_bao: list[str] — danh sách cảnh báo tiên quyết, tín chỉ, xung đột lịch
        - tong_mon_hoc_lai: int
        - tong_tin_chi_hoc_lai: int
        - tim_thay: bool
    """
    # --- Bước 1: Lấy hồ sơ sinh viên ---
    ho_so = lay_ho_so_sinh_vien(ma_sv, tool_context)
    if not ho_so.get("tim_thay"):
        return {**ho_so, "lo_trinh": [], "canh_bao": [], "tim_thay": False}

    mon_truot_no: list[dict] = ho_so["mon_truot_no"]
    nganh = ho_so["nganh"]

    if not mon_truot_no:
        return {
            "ma_sv": ma_sv,
            "ho_ten": ho_so["ho_ten"],
            "nganh": nganh,
            "lo_trinh": [],
            "canh_bao": ["Sinh viên không có môn trượt/nợ nào. Không cần lập lộ trình học lại."],
            "tong_mon_hoc_lai": 0,
            "tong_tin_chi_hoc_lai": 0,
            "tim_thay": True,
        }

    # Loại bỏ trùng lặp: giữ bản ghi đầu tiên cho mỗi ma_mon
    seen_ma: dict[str, dict] = {}
    for m in mon_truot_no:
        ma = m["ma_mon"]
        if ma not in seen_ma:
            seen_ma[ma] = m
    mon_truot_no = list(seen_ma.values())

    # --- Bước 2: Lấy chương trình đào tạo ---
    cdt = lay_chuong_trinh_dao_tao(nganh, tool_context)
    mon_hoc_cdt: list[dict] = cdt.get("mon_hoc", []) if cdt.get("tim_thay") else []

    # Map mã môn -> thông tin môn trong CDT
    map_cdt: dict[str, dict] = {m["ma_mon"]: m for m in mon_hoc_cdt}

    # Các môn đã đạt (để kiểm tra tiên quyết)
    ma_da_dat = {
        r["ma_mon"] for r in ho_so["bang_diem"]
        if r.get("trang_thai", "").strip().lower() == "dat"
    }

    canh_bao: list[str] = []

    # --- Bước 3: Xây dựng đồ thị tiên quyết và topo-sort ---
    # Chỉ xét các môn trượt/nợ
    ma_truot_no = {m["ma_mon"] for m in mon_truot_no}

    # Adjacency list: mon A -> [mon B cần A làm tiên quyết]
    do_thi: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {m["ma_mon"]: 0 for m in mon_truot_no}

    for mon in mon_truot_no:
        ma = mon["ma_mon"]
        cdt_info = map_cdt.get(ma, {})
        tien_quyet: list[str] = cdt_info.get("tien_quyet", [])
        for tq in tien_quyet:
            if tq in ma_truot_no:
                # tq phải học trước ma
                do_thi[tq].append(ma)
                in_degree[ma] = in_degree.get(ma, 0) + 1
            elif tq not in ma_da_dat:
                canh_bao.append(
                    f"Môn {ma} ({mon['ten_mon']}) yêu cầu tiên quyết '{tq}' "
                    f"chưa hoàn thành. Cần hoàn thành '{tq}' trước."
                )

    # Kahn's algorithm topo-sort
    hang_doi: deque[str] = deque(
        [m for m, d in in_degree.items() if d == 0]
    )
    thu_tu: list[str] = []
    while hang_doi:
        ma = hang_doi.popleft()
        thu_tu.append(ma)
        for ke in do_thi[ma]:
            in_degree[ke] -= 1
            if in_degree[ke] == 0:
                hang_doi.append(ke)

    # Nếu có cycle (rất hiếm trong CDT thực tế)
    if len(thu_tu) < len(in_degree):
        canh_bao.append(
            "Phát hiện vòng lặp trong quan hệ tiên quyết. "
            "Vui lòng kiểm tra lại chương trình đào tạo."
        )
        # Thêm các môn còn lại theo thứ tự bất kỳ
        da_them = set(thu_tu)
        for ma in in_degree:
            if ma not in da_them:
                thu_tu.append(ma)

    # Map mã môn -> thông tin đầy đủ
    map_mon_truot: dict[str, dict] = {m["ma_mon"]: m for m in mon_truot_no}

    # --- Bước 4: Xếp lịch theo kỳ với giới hạn tín chỉ ---
    lo_trinh: list[dict] = []
    ky_so = 1
    ma_hoc_xong: set[str] = set(ma_da_dat)  # các môn đã hoàn thành (kể cả các kỳ trước trong lộ trình)
    con_lai = list(thu_tu)  # thứ tự topo

    while con_lai:
        ky_mon: list[dict] = []
        tin_chi_ky = 0
        dua_vao_ky_sau: list[str] = []

        for ma in con_lai:
            mon = map_mon_truot[ma]
            tc = int(mon.get("tin_chi", 3) or 3)
            cdt_info = map_cdt.get(ma, {})
            tien_quyet = cdt_info.get("tien_quyet", [])

            # Kiểm tra tiên quyết đã hoàn thành chưa
            tq_chua_dat = [tq for tq in tien_quyet if tq not in ma_hoc_xong]
            if tq_chua_dat:
                dua_vao_ky_sau.append(ma)
                continue

            # Kiểm tra giới hạn tín chỉ
            if tin_chi_ky + tc > so_tin_chi_toi_da_moi_ky:
                dua_vao_ky_sau.append(ma)
                continue

            ky_mon.append({
                "ma_mon": ma,
                "ten_mon": mon["ten_mon"],
                "tin_chi": tc,
                "diem_cu": mon.get("diem_chu", ""),
                "ghi_chu": f"Học lại kỳ {ky_so}",
            })
            tin_chi_ky += tc

        if not ky_mon:
            # Không tiến triển được — thoát để tránh vòng lặp vô tận
            canh_bao.append(
                f"Không thể xếp lịch cho {len(con_lai)} môn còn lại "
                f"do ràng buộc tiên quyết hoặc tín chỉ. "
                f"Các môn chưa xếp được: {', '.join(con_lai)}"
            )
            break

        # Đánh dấu các môn trong kỳ này là đã hoàn thành (dự kiến)
        ma_hoc_xong.update(m["ma_mon"] for m in ky_mon)

        lo_trinh.append({
            "ky_hoc_lai": f"Kỳ học lại {ky_so}",
            "mon_hoc": ky_mon,
            "tong_tin_chi": tin_chi_ky,
        })
        con_lai = dua_vao_ky_sau
        ky_so += 1

        # Giới hạn an toàn
        if ky_so > 20:
            canh_bao.append("Lộ trình kéo dài quá 20 kỳ. Vui lòng xem xét lại.")
            break

    # --- Bước 5: Kiểm tra xung đột lịch học ---
    lich_rows = _doc_csv(_LICH_HOC_FILE)
    # Map mã môn -> list lịch
    lich_map: dict[str, list[dict]] = defaultdict(list)
    for r in lich_rows:
        lich_map[r.get("ma_mon", "")].append(r)

    for ky_info in lo_trinh:
        ma_ky = [m["ma_mon"] for m in ky_info["mon_hoc"]]
        # Kiểm tra trùng (thu, tiet) giữa các môn trong cùng kỳ
        slot_map: dict[tuple, str] = {}
        for ma in ma_ky:
            for lich in lich_map.get(ma, []):
                key = (lich.get("thu", ""), lich.get("tiet", ""))
                if key in slot_map:
                    canh_bao.append(
                        f"Xung đột lịch trong {ky_info['ky_hoc_lai']}: "
                        f"môn {ma} và môn {slot_map[key]} "
                        f"đều có lịch vào {key[0]}, tiết {key[1]}."
                    )
                else:
                    slot_map[key] = ma

    tong_mon = sum(len(k["mon_hoc"]) for k in lo_trinh)
    tong_tc = sum(k["tong_tin_chi"] for k in lo_trinh)

    return {
        "ma_sv": ma_sv,
        "ho_ten": ho_so["ho_ten"],
        "nganh": nganh,
        "lo_trinh": lo_trinh,
        "canh_bao": canh_bao,
        "tong_mon_hoc_lai": tong_mon,
        "tong_tin_chi_hoc_lai": tong_tc,
        "tim_thay": True,
    }


# ---------------------------------------------------------------------------
# 5. Tra cứu lịch học
# ---------------------------------------------------------------------------

def lay_lich_hoc(ma_sv: str, tool_context=None) -> dict:
    """
    Lấy lịch học của sinh viên dựa trên các môn đang đăng ký.

    Args:
        ma_sv: Mã sinh viên.
        tool_context: ADK ToolContext.

    Returns:
        dict với:
        - ma_sv: Mã sinh viên.
        - lich_hoc: list[dict] — danh sách lịch {ma_mon, ten_mon, lop, thu, tiet, phong, ky}.
        - tim_thay: bool.
    """
    ho_so = lay_ho_so_sinh_vien(ma_sv, tool_context)
    if not ho_so.get("tim_thay"):
        return {**ho_so, "lich_hoc": [], "tim_thay": False}

    # Lấy các môn sinh viên đang học (kỳ gần nhất, chưa có kết quả cuối)
    bang_diem = ho_so.get("bang_diem", [])
    ky_hien_tai = max((r["ky"] for r in bang_diem), default="") if bang_diem else ""
    ma_mon_hoc = {r["ma_mon"] for r in bang_diem if r.get("ky") == ky_hien_tai}

    lich_rows = _doc_csv(_LICH_HOC_FILE)
    lich_sv = [
        {
            "ma_mon": r["ma_mon"],
            "lop": r.get("lop", ""),
            "thu": r.get("thu", ""),
            "tiet": r.get("tiet", ""),
            "phong": r.get("phong", ""),
            "ky": r.get("ky", ""),
        }
        for r in lich_rows
        if r.get("ma_mon") in ma_mon_hoc
    ]

    return {
        "ma_sv": ma_sv,
        "ho_ten": ho_so["ho_ten"],
        "ky_hien_tai": ky_hien_tai,
        "lich_hoc": lich_sv,
        "tim_thay": True,
    }


# ---------------------------------------------------------------------------
# 6. Tra cứu bảng điểm
# ---------------------------------------------------------------------------

def lay_bang_diem(ma_sv: str, tool_context=None) -> dict:
    """
    Lấy bảng điểm toàn bộ của sinh viên.

    Args:
        ma_sv: Mã sinh viên (8-12 chữ số).
        tool_context: ADK ToolContext.

    Returns:
        dict giống lay_ho_so_sinh_vien nhưng tập trung vào bang_diem và thống kê.
    """
    ho_so = lay_ho_so_sinh_vien(ma_sv, tool_context)
    if not ho_so.get("tim_thay"):
        return {**ho_so, "bang_diem": [], "tim_thay": False}

    bang_diem = ho_so["bang_diem"]

    # Tính GPA (thang 4 và thang 10)
    tong_tc = sum(m["tin_chi"] for m in bang_diem if m["trang_thai"] == "dat")
    tong_diem_tc = sum(m["diem_so"] * m["tin_chi"] for m in bang_diem if m["trang_thai"] == "dat")
    gpa_10 = round(tong_diem_tc / tong_tc, 2) if tong_tc > 0 else 0.0

    # Quy đổi sang thang 4 (đơn giản)
    def _doi_thang_4(diem: float) -> float:
        if diem >= 8.5:
            return 4.0
        elif diem >= 8.0:
            return 3.7
        elif diem >= 7.0:
            return 3.0
        elif diem >= 6.5:
            return 2.5
        elif diem >= 5.5:
            return 2.0
        elif diem >= 5.0:
            return 1.5
        elif diem >= 4.0:
            return 1.0
        else:
            return 0.0

    tong_diem_tc_4 = sum(
        _doi_thang_4(m["diem_so"]) * m["tin_chi"]
        for m in bang_diem if m["trang_thai"] == "dat"
    )
    gpa_4 = round(tong_diem_tc_4 / tong_tc, 2) if tong_tc > 0 else 0.0

    return {
        "ma_sv": ma_sv,
        "ho_ten": ho_so["ho_ten"],
        "nganh": ho_so["nganh"],
        "bang_diem": bang_diem,
        "mon_truot_no": ho_so["mon_truot_no"],
        "tong_tin_chi_dat": tong_tc,
        "gpa_thang_10": gpa_10,
        "gpa_thang_4": gpa_4,
        "tim_thay": True,
    }


# ---------------------------------------------------------------------------
# 7. Tạo biểu mẫu
# ---------------------------------------------------------------------------

def tao_bieu_mau(loai_mau: str, du_lieu: dict, tool_context=None) -> str:
    """
    Tạo biểu mẫu theo dõi giáo vụ dạng text/markdown.

    Các loại biểu mẫu hỗ trợ:
    - 'ke_hoach_hoc_lai': Kế hoạch học lại/trả nợ học phần
    - 'canh_bao_hoc_vu': Thông báo cảnh báo học vụ
    - 'xac_nhan_dang_ky': Xác nhận đăng ký học phần

    Args:
        loai_mau: Loại biểu mẫu cần tạo.
        du_lieu: Dữ liệu điền vào biểu mẫu (dict linh hoạt).
        tool_context: ADK ToolContext.

    Returns:
        Chuỗi nội dung biểu mẫu đã được điền dữ liệu (Markdown).
    """
    ngay_tao = datetime.now().strftime("%d/%m/%Y")

    if loai_mau == "ke_hoach_hoc_lai":
        ma_sv = du_lieu.get("ma_sv", "N/A")
        ho_ten = du_lieu.get("ho_ten", "N/A")
        nganh = du_lieu.get("nganh", "N/A")
        lo_trinh = du_lieu.get("lo_trinh", [])
        canh_bao = du_lieu.get("canh_bao", [])

        dong = [
            "# TRƯỜNG ĐẠI HỌC ĐẠI NAM",
            "## PHÒNG GIÁO VỤ — KẾ HOẠCH HỌC LẠI / TRẢ NỢ HỌC PHẦN",
            f"**Ngày lập:** {ngay_tao}",
            "",
            f"**Mã sinh viên:** {ma_sv}",
            f"**Họ tên:** {ho_ten}",
            f"**Ngành:** {nganh}",
            "",
            "---",
            "## Lộ trình học lại theo kỳ",
            "",
        ]

        for ky in lo_trinh:
            dong.append(f"### {ky.get('ky_hoc_lai', 'Kỳ ?')} — Tổng: {ky.get('tong_tin_chi', 0)} tín chỉ")
            dong.append("| STT | Mã môn | Tên môn | Tín chỉ | Điểm cũ | Ghi chú |")
            dong.append("|-----|--------|---------|---------|---------|---------|")
            for i, mon in enumerate(ky.get("mon_hoc", []), 1):
                dong.append(
                    f"| {i} | {mon.get('ma_mon','')} | {mon.get('ten_mon','')} "
                    f"| {mon.get('tin_chi',0)} | {mon.get('diem_cu','')} "
                    f"| {mon.get('ghi_chu','')} |"
                )
            dong.append("")

        if canh_bao:
            dong.append("## ⚠️ Cảnh báo")
            for cb in canh_bao:
                dong.append(f"- {cb}")
            dong.append("")

        dong.extend([
            "---",
            "**Cán bộ giáo vụ:** ___________________",
            "**Sinh viên xác nhận:** ___________________",
            f"*Biểu mẫu được tạo tự động bởi Trợ lý Giáo vụ Đại Nam ngày {ngay_tao}*",
        ])
        return "\n".join(dong)

    elif loai_mau == "canh_bao_hoc_vu":
        ma_sv = du_lieu.get("ma_sv", "N/A")
        ho_ten = du_lieu.get("ho_ten", "N/A")
        muc_canh_bao = du_lieu.get("muc_canh_bao", "Mức 1")
        noi_dung = du_lieu.get("noi_dung", "")

        return "\n".join([
            "# TRƯỜNG ĐẠI HỌC ĐẠI NAM",
            "## THÔNG BÁO CẢNH BÁO HỌC VỤ",
            f"**Ngày:** {ngay_tao}",
            "",
            f"**Mã sinh viên:** {ma_sv}",
            f"**Họ tên:** {ho_ten}",
            f"**Mức cảnh báo:** {muc_canh_bao}",
            "",
            "**Nội dung:**",
            noi_dung,
            "",
            "---",
            "Sinh viên cần liên hệ phòng Giáo vụ để được hướng dẫn xử lý.",
            f"*Thông báo tự động — {ngay_tao}*",
        ])

    elif loai_mau == "xac_nhan_dang_ky":
        ma_sv = du_lieu.get("ma_sv", "N/A")
        ho_ten = du_lieu.get("ho_ten", "N/A")
        danh_sach_mon = du_lieu.get("danh_sach_mon", [])

        dong = [
            "# TRƯỜNG ĐẠI HỌC ĐẠI NAM",
            "## XÁC NHẬN ĐĂNG KÝ HỌC PHẦN",
            f"**Ngày:** {ngay_tao}",
            "",
            f"**Mã sinh viên:** {ma_sv}",
            f"**Họ tên:** {ho_ten}",
            "",
            "| STT | Mã môn | Tên môn | Tín chỉ |",
            "|-----|--------|---------|---------|",
        ]
        for i, mon in enumerate(danh_sach_mon, 1):
            if isinstance(mon, dict):
                dong.append(f"| {i} | {mon.get('ma_mon','')} | {mon.get('ten_mon','')} | {mon.get('tin_chi',0)} |")
            else:
                dong.append(f"| {i} | — | {mon} | — |")
        dong.extend([
            "",
            "**Cán bộ giáo vụ:** ___________________",
            f"*Biểu mẫu tự động — {ngay_tao}*",
        ])
        return "\n".join(dong)

    else:
        return (
            f"# Biểu mẫu: {loai_mau}\n"
            f"**Ngày tạo:** {ngay_tao}\n\n"
            + "\n".join(f"- **{k}:** {v}" for k, v in du_lieu.items())
            + f"\n\n*Biểu mẫu tạo bởi Trợ lý Giáo vụ Đại Nam — {ngay_tao}*"
        )


# ---------------------------------------------------------------------------
# 8. Ghi nhật ký yêu cầu
# ---------------------------------------------------------------------------

def ghi_nhat_ky_yeu_cau(
    loai_yeu_cau: str,
    ma_sv: str,
    ket_qua_tom_tat: str,
    can_bo: str,
    tool_context=None,
) -> dict:
    """
    Ghi lại yêu cầu đã xử lý vào file nhật ký CSV (data/nhat_ky_yeu_cau.csv).

    Dữ liệu này là nguồn cho Báo cáo xử lý yêu cầu trên dashboard.

    Args:
        loai_yeu_cau: Loại yêu cầu đã xử lý.
        ma_sv: Mã sinh viên liên quan (hoặc chuỗi rỗng nếu không có).
        ket_qua_tom_tat: Tóm tắt ngắn kết quả xử lý (không ghi PII chi tiết).
        can_bo: Mã/tên cán bộ giáo vụ thực hiện.
        tool_context: ADK ToolContext (dùng để lấy vai_tro từ session state).

    Returns:
        dict {thanh_cong: bool, thoi_gian: str, thong_bao: str}
    """
    vai_tro = "he_thong"
    if tool_context is not None:
        try:
            state = tool_context.state if hasattr(tool_context, "state") else {}
            vai_tro = state.get("vai_tro", "he_thong")
        except Exception:
            pass

    thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = ["thoi_gian", "can_bo", "vai_tro", "loai_yeu_cau", "ma_sv", "ket_qua_tom_tat"]
    row = {
        "thoi_gian": thoi_gian,
        "can_bo": can_bo,
        "vai_tro": vai_tro,
        "loai_yeu_cau": loai_yeu_cau,
        "ma_sv": ma_sv,
        "ket_qua_tom_tat": ket_qua_tom_tat[:200],  # giới hạn độ dài
    }

    try:
        file_ton_tai = _NHAT_KY_FILE.exists() and _NHAT_KY_FILE.stat().st_size > 0
        with open(_NHAT_KY_FILE, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            if not file_ton_tai:
                writer.writeheader()
            writer.writerow(row)
        return {
            "thanh_cong": True,
            "thoi_gian": thoi_gian,
            "thong_bao": "Đã ghi nhật ký yêu cầu thành công.",
        }
    except Exception as e:
        return {
            "thanh_cong": False,
            "thoi_gian": thoi_gian,
            "thong_bao": f"Lỗi khi ghi nhật ký: {e}",
        }
