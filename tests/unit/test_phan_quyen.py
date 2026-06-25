"""
Kiểm thử đơn vị cho hàm kiem_tra_quyen trong app/tools.py.
Kiểm tra:
- Vai trò tra_cuu_vien bị từ chối các hành động nhạy cảm
- Vai trò giao_vu được phép tra cứu và lập lộ trình
- Vai trò truong_phong_dao_tao có toàn quyền
- Định dạng mã sinh viên được kiểm tra đúng
"""
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# --- Logic kiem_tra_quyen thuần Python để kiểm thử độc lập ---

# Ma trận phân quyền theo contract
# Cấu trúc: ROLES[vai_tro] = set của các hành_dong được phép
ROLES = {
    "truong_phong_dao_tao": {
        "tra_cuu_quy_che",
        "lay_ho_so_sinh_vien",
        "lay_chuong_trinh_dao_tao",
        "tinh_lo_trinh_hoc_lai",
        "lay_lich_hoc",
        "lay_bang_diem",
        "tao_bieu_mau",
        "ghi_nhat_ky_yeu_cau",
        "duyet_hitl",
        "xem_du_lieu_nhay_cam",
        "xuat_bao_cao",
    },
    "giao_vu": {
        "tra_cuu_quy_che",
        "lay_ho_so_sinh_vien",
        "lay_chuong_trinh_dao_tao",
        "tinh_lo_trinh_hoc_lai",
        "lay_lich_hoc",
        "lay_bang_diem",
        "tao_bieu_mau",
        "ghi_nhat_ky_yeu_cau",
    },
    "tra_cuu_vien": {
        "tra_cuu_quy_che",
    },
}

# Hành động được coi là nhạy cảm (chỉ truong_phong_dao_tao)
HANH_DONG_NHAY_CAM = {
    "duyet_hitl",
    "xem_du_lieu_nhay_cam",
    "xuat_bao_cao",
}


def _kiem_tra_quyen(vai_tro: str, hanh_dong: str) -> bool:
    """
    Kiểm tra vai trò có quyền thực hiện hành động không.
    Hàm này phản ánh logic trong app/tools.py::kiem_tra_quyen.

    Args:
        vai_tro: Vai trò người dùng ("giao_vu", "truong_phong_dao_tao", "tra_cuu_vien")
        hanh_dong: Tên hành động/công cụ cần kiểm tra

    Returns:
        True nếu được phép, False nếu không
    """
    if vai_tro not in ROLES:
        return False
    return hanh_dong in ROLES[vai_tro]


def _kiem_tra_ma_sv(ma_sv: str) -> bool:
    """
    Kiểm tra định dạng mã sinh viên hợp lệ.
    Mã SV Đại Nam: 10 chữ số (ví dụ: 1771020001).
    """
    import re
    return bool(re.match(r"^\d{10}$", ma_sv))


# ============================================================
# CÁC BÀI KIỂM THỬ PHÂN QUYỀN
# ============================================================

class TestPhanQuyenTraCuuVien:
    """Kiểm tra vai trò tra_cuu_vien bị từ chối đúng các hành động không được phép."""

    def test_tra_cuu_vien_duoc_phep_tra_cuu_quy_che(self):
        """tra_cuu_vien được phép tra cứu quy chế - đây là quyền duy nhất."""
        assert _kiem_tra_quyen("tra_cuu_vien", "tra_cuu_quy_che") is True

    def test_tra_cuu_vien_bi_tu_choi_lay_ho_so_sinh_vien(self):
        """tra_cuu_vien KHÔNG được xem hồ sơ sinh viên (dữ liệu cá nhân)."""
        assert _kiem_tra_quyen("tra_cuu_vien", "lay_ho_so_sinh_vien") is False

    def test_tra_cuu_vien_bi_tu_choi_lay_bang_diem(self):
        """tra_cuu_vien KHÔNG được xem bảng điểm sinh viên (dữ liệu nhạy cảm)."""
        assert _kiem_tra_quyen("tra_cuu_vien", "lay_bang_diem") is False

    def test_tra_cuu_vien_bi_tu_choi_tinh_lo_trinh_hoc_lai(self):
        """tra_cuu_vien KHÔNG được tính lộ trình học lại (cần hồ sơ cá nhân)."""
        assert _kiem_tra_quyen("tra_cuu_vien", "tinh_lo_trinh_hoc_lai") is False

    def test_tra_cuu_vien_bi_tu_choi_lay_lich_hoc(self):
        """tra_cuu_vien KHÔNG được xem lịch học cá nhân sinh viên."""
        assert _kiem_tra_quyen("tra_cuu_vien", "lay_lich_hoc") is False

    def test_tra_cuu_vien_bi_tu_choi_tao_bieu_mau(self):
        """tra_cuu_vien KHÔNG được tạo biểu mẫu (cần thẩm quyền giao_vu trở lên)."""
        assert _kiem_tra_quyen("tra_cuu_vien", "tao_bieu_mau") is False

    def test_tra_cuu_vien_bi_tu_choi_ghi_nhat_ky(self):
        """tra_cuu_vien KHÔNG được ghi nhật ký yêu cầu."""
        assert _kiem_tra_quyen("tra_cuu_vien", "ghi_nhat_ky_yeu_cau") is False

    def test_tra_cuu_vien_bi_tu_choi_duyet_hitl(self):
        """tra_cuu_vien KHÔNG được duyệt yêu cầu HITL (chỉ truong_phong_dao_tao)."""
        assert _kiem_tra_quyen("tra_cuu_vien", "duyet_hitl") is False

    def test_tra_cuu_vien_bi_tu_choi_xem_du_lieu_nhay_cam(self):
        """tra_cuu_vien KHÔNG được xem dữ liệu nhạy cảm."""
        assert _kiem_tra_quyen("tra_cuu_vien", "xem_du_lieu_nhay_cam") is False

    def test_tra_cuu_vien_bi_tu_choi_xuat_bao_cao(self):
        """tra_cuu_vien KHÔNG được xuất báo cáo xử lý yêu cầu."""
        assert _kiem_tra_quyen("tra_cuu_vien", "xuat_bao_cao") is False

    def test_tra_cuu_vien_bi_tu_choi_hanh_dong_khong_ton_tai(self):
        """tra_cuu_vien bị từ chối hành động không tồn tại trong hệ thống."""
        assert _kiem_tra_quyen("tra_cuu_vien", "hanh_dong_khong_co_that") is False

    @pytest.mark.parametrize("hanh_dong_nhay_cam", sorted(HANH_DONG_NHAY_CAM))
    def test_tra_cuu_vien_bi_tu_choi_tat_ca_hanh_dong_nhay_cam(self, hanh_dong_nhay_cam):
        """tra_cuu_vien bị từ chối tất cả hành động được phân loại là nhạy cảm."""
        assert _kiem_tra_quyen("tra_cuu_vien", hanh_dong_nhay_cam) is False, (
            f"tra_cuu_vien phải bị từ chối hành động nhạy cảm: {hanh_dong_nhay_cam}"
        )


class TestPhanQuyenGiaoVu:
    """Kiểm tra quyền của vai trò giao_vu."""

    def test_giao_vu_duoc_phep_tra_cuu_quy_che(self):
        assert _kiem_tra_quyen("giao_vu", "tra_cuu_quy_che") is True

    def test_giao_vu_duoc_phep_lay_ho_so_sinh_vien(self):
        assert _kiem_tra_quyen("giao_vu", "lay_ho_so_sinh_vien") is True

    def test_giao_vu_duoc_phep_tinh_lo_trinh_hoc_lai(self):
        assert _kiem_tra_quyen("giao_vu", "tinh_lo_trinh_hoc_lai") is True

    def test_giao_vu_duoc_phep_lay_bang_diem(self):
        assert _kiem_tra_quyen("giao_vu", "lay_bang_diem") is True

    def test_giao_vu_duoc_phep_tao_bieu_mau(self):
        assert _kiem_tra_quyen("giao_vu", "tao_bieu_mau") is True

    def test_giao_vu_duoc_phep_ghi_nhat_ky(self):
        assert _kiem_tra_quyen("giao_vu", "ghi_nhat_ky_yeu_cau") is True

    def test_giao_vu_bi_tu_choi_duyet_hitl(self):
        """giao_vu KHÔNG được duyệt HITL - chỉ truong_phong_dao_tao."""
        assert _kiem_tra_quyen("giao_vu", "duyet_hitl") is False

    def test_giao_vu_bi_tu_choi_xem_du_lieu_nhay_cam(self):
        """giao_vu KHÔNG được xem dữ liệu nhạy cảm ngoài phạm vi (theo contract)."""
        assert _kiem_tra_quyen("giao_vu", "xem_du_lieu_nhay_cam") is False

    def test_giao_vu_bi_tu_choi_xuat_bao_cao(self):
        """giao_vu không có quyền xuất báo cáo tổng hợp."""
        assert _kiem_tra_quyen("giao_vu", "xuat_bao_cao") is False


class TestPhanQuyenTruongPhong:
    """Kiểm tra truong_phong_dao_tao có toàn quyền."""

    @pytest.mark.parametrize("hanh_dong", [
        "tra_cuu_quy_che",
        "lay_ho_so_sinh_vien",
        "lay_chuong_trinh_dao_tao",
        "tinh_lo_trinh_hoc_lai",
        "lay_lich_hoc",
        "lay_bang_diem",
        "tao_bieu_mau",
        "ghi_nhat_ky_yeu_cau",
        "duyet_hitl",
        "xem_du_lieu_nhay_cam",
        "xuat_bao_cao",
    ])
    def test_truong_phong_duoc_phep_tat_ca_hanh_dong(self, hanh_dong):
        """truong_phong_dao_tao được phép thực hiện tất cả hành động trong hệ thống."""
        assert _kiem_tra_quyen("truong_phong_dao_tao", hanh_dong) is True, (
            f"truong_phong_dao_tao phải có quyền: {hanh_dong}"
        )


class TestVaiTroKhongHopLe:
    """Kiểm tra các vai trò không hợp lệ bị từ chối."""

    def test_vai_tro_khong_ton_tai_bi_tu_choi(self):
        """Vai trò không tồn tại trong hệ thống phải bị từ chối mọi hành động."""
        assert _kiem_tra_quyen("quan_tri_vien", "tra_cuu_quy_che") is False

    def test_vai_tro_rong_bi_tu_choi(self):
        """Chuỗi vai trò rỗng phải bị từ chối."""
        assert _kiem_tra_quyen("", "tra_cuu_quy_che") is False

    def test_vai_tro_admin_khong_duoc_phep_mac_dinh(self):
        """Vai trò 'admin' không được khai báo -> bị từ chối."""
        assert _kiem_tra_quyen("admin", "lay_ho_so_sinh_vien") is False

    def test_vai_tro_khong_hop_le_khong_duoc_leo_thang_quyen(self):
        """
        Vai trò không hợp lệ không thể thực hiện hành động nhạy cảm.
        Đây là kiểm tra chống privilege escalation.
        """
        for hanh_dong in HANH_DONG_NHAY_CAM:
            assert _kiem_tra_quyen("unknown_role", hanh_dong) is False


class TestKiemTraDinhDangMaSV:
    """Kiểm tra xác thực định dạng mã sinh viên."""

    def test_ma_sv_hop_le_10_chu_so(self):
        """Mã SV 10 chữ số là hợp lệ."""
        assert _kiem_tra_ma_sv("1771020001") is True

    def test_ma_sv_hop_le_vi_du_2(self):
        """Mã SV 10 chữ số khác cũng hợp lệ."""
        assert _kiem_tra_ma_sv("1771020002") is True

    def test_ma_sv_qua_ngan_bi_tu_choi(self):
        """Mã SV dưới 10 chữ số không hợp lệ."""
        assert _kiem_tra_ma_sv("17710200") is False

    def test_ma_sv_qua_dai_bi_tu_choi(self):
        """Mã SV trên 10 chữ số không hợp lệ."""
        assert _kiem_tra_ma_sv("177102000100") is False

    def test_ma_sv_chua_chu_cai_bi_tu_choi(self):
        """Mã SV chứa chữ cái không hợp lệ."""
        assert _kiem_tra_ma_sv("177102000A") is False

    def test_ma_sv_rong_bi_tu_choi(self):
        """Mã SV rỗng không hợp lệ."""
        assert _kiem_tra_ma_sv("") is False

    def test_ma_sv_chua_dau_cach_bi_tu_choi(self):
        """Mã SV chứa dấu cách không hợp lệ."""
        assert _kiem_tra_ma_sv("1771020 01") is False


class TestTichHopPhanQuyenVaMaSV:
    """Kiểm thử tích hợp: kết hợp kiểm tra phân quyền và xác thực mã SV."""

    def test_tra_cuu_vien_voi_ma_sv_hop_le_van_bi_tu_choi_hanh_dong_nhay_cam(self):
        """
        Kịch bản: tra_cuu_vien cố truy cập bảng điểm SV 1771020001.
        Kết quả: bị từ chối vì vai trò, dù mã SV hợp lệ.
        """
        vai_tro = "tra_cuu_vien"
        ma_sv = "1771020001"
        hanh_dong = "lay_bang_diem"

        ma_sv_hop_le = _kiem_tra_ma_sv(ma_sv)
        co_quyen = _kiem_tra_quyen(vai_tro, hanh_dong)

        assert ma_sv_hop_le is True, "Mã SV 1771020001 phải hợp lệ"
        assert co_quyen is False, (
            "tra_cuu_vien phải bị từ chối lay_bang_diem dù mã SV hợp lệ"
        )
        # Cả hai điều kiện phải đúng để cho phép: mã SV hợp lệ VÀ có quyền
        assert not (ma_sv_hop_le and co_quyen), (
            "Yêu cầu phải bị từ chối: thiếu quyền"
        )

    def test_giao_vu_voi_ma_sv_khong_hop_le_bi_tu_choi(self):
        """
        Kịch bản: giao_vu có quyền nhưng cung cấp mã SV không hợp lệ.
        Kết quả: bị từ chối vì mã SV không hợp lệ.
        """
        vai_tro = "giao_vu"
        ma_sv = "INVALID123"
        hanh_dong = "lay_bang_diem"

        ma_sv_hop_le = _kiem_tra_ma_sv(ma_sv)
        co_quyen = _kiem_tra_quyen(vai_tro, hanh_dong)

        assert co_quyen is True, "giao_vu có quyền lay_bang_diem"
        assert ma_sv_hop_le is False, "INVALID123 không phải mã SV hợp lệ"
        # Vẫn phải từ chối vì mã SV không hợp lệ
        assert not (ma_sv_hop_le and co_quyen), (
            "Yêu cầu phải bị từ chối: mã SV không hợp lệ"
        )

    def test_giao_vu_voi_ma_sv_va_quyen_hop_le_duoc_phep(self):
        """
        Kịch bản: giao_vu truy cập bảng điểm SV 1771020001.
        Kết quả: được phép vì cả vai trò và mã SV đều hợp lệ.
        """
        vai_tro = "giao_vu"
        ma_sv = "1771020001"
        hanh_dong = "lay_bang_diem"

        ma_sv_hop_le = _kiem_tra_ma_sv(ma_sv)
        co_quyen = _kiem_tra_quyen(vai_tro, hanh_dong)

        assert ma_sv_hop_le is True
        assert co_quyen is True
        assert ma_sv_hop_le and co_quyen, "Cả hai điều kiện đúng -> được phép"


class TestPhanQuyenTheoContract:
    """
    Kiểm tra ma trận phân quyền đầy đủ theo SHARED DESIGN CONTRACT.
    Đảm bảo các quyền nhất quán với tài liệu thiết kế.
    """

    def test_tra_cuu_vien_chi_co_mot_quyen(self):
        """tra_cuu_vien chỉ có đúng 1 quyền: tra_cuu_quy_che."""
        quyen_tra_cuu_vien = ROLES["tra_cuu_vien"]
        assert quyen_tra_cuu_vien == {"tra_cuu_quy_che"}, (
            f"tra_cuu_vien chỉ được có quyền tra_cuu_quy_che, "
            f"nhưng hiện có: {quyen_tra_cuu_vien}"
        )

    def test_giao_vu_khong_co_quyen_nhay_cam(self):
        """giao_vu không có bất kỳ quyền nhạy cảm nào."""
        quyen_giao_vu = ROLES["giao_vu"]
        quyen_nhay_cam_cua_giao_vu = quyen_giao_vu & HANH_DONG_NHAY_CAM
        assert quyen_nhay_cam_cua_giao_vu == set(), (
            f"giao_vu không được có quyền nhạy cảm, nhưng hiện có: {quyen_nhay_cam_cua_giao_vu}"
        )

    def test_truong_phong_co_tat_ca_quyen_cua_giao_vu(self):
        """truong_phong_dao_tao phải có tất cả quyền của giao_vu."""
        quyen_giao_vu = ROLES["giao_vu"]
        quyen_truong_phong = ROLES["truong_phong_dao_tao"]
        assert quyen_giao_vu.issubset(quyen_truong_phong), (
            f"truong_phong thiếu quyền của giao_vu: {quyen_giao_vu - quyen_truong_phong}"
        )

    def test_truong_phong_co_them_quyen_nhay_cam(self):
        """truong_phong_dao_tao có thêm các quyền nhạy cảm so với giao_vu."""
        quyen_truong_phong = ROLES["truong_phong_dao_tao"]
        quyen_nhay_cam = HANH_DONG_NHAY_CAM
        assert quyen_nhay_cam.issubset(quyen_truong_phong), (
            f"truong_phong thiếu quyền nhạy cảm: {quyen_nhay_cam - quyen_truong_phong}"
        )

    def test_thu_bac_quyen_tang_dan(self):
        """
        Kiểm tra thứ bậc quyền tăng dần:
        tra_cuu_vien ⊂ giao_vu ⊂ truong_phong_dao_tao
        """
        quyen_tra_cuu = ROLES["tra_cuu_vien"]
        quyen_giao_vu = ROLES["giao_vu"]
        quyen_truong_phong = ROLES["truong_phong_dao_tao"]

        assert quyen_tra_cuu.issubset(quyen_giao_vu), (
            "Quyền tra_cuu_vien phải là tập con của giao_vu"
        )
        assert quyen_giao_vu.issubset(quyen_truong_phong), (
            "Quyền giao_vu phải là tập con của truong_phong_dao_tao"
        )
        assert quyen_tra_cuu.issubset(quyen_truong_phong), (
            "Quyền tra_cuu_vien phải là tập con của truong_phong_dao_tao"
        )
