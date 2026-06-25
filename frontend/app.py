"""
frontend/app.py — Dashboard giáo vụ nội bộ Đại học Đại Nam
=============================================================
Chạy:
    pip install flask
    FASTAPI_URL=http://localhost:8000 flask --app frontend.app run --port 5000

Biến môi trường:
    FASTAPI_URL  — URL gốc của ADK FastAPI (mặc định: http://localhost:8000)
    SECRET_KEY   — khoá bí mật Flask session (mặc định: dev)
"""

import csv
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# ─────────────────────────────────────────
# Cấu hình
# ─────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent  # Capstone_GiaoVu_DaiNam/
DATA_DIR = BASE_DIR / "data"
NHAT_KY_CSV = DATA_DIR / "nhat_ky_yeu_cau.csv"

FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")

# Vai trò hợp lệ và nhãn hiển thị tiếng Việt
VAI_TRO_LABELS = {
    "giao_vu": "Cán bộ Giáo vụ",
    "truong_phong_dao_tao": "Trưởng phòng Đào tạo",
    "tra_cuu_vien": "Tra cứu viên",
}


def create_app() -> Flask:
    """Tạo và cấu hình Flask app."""
    app = Flask(
        __name__,
        template_folder="templates",
    )
    app.secret_key = os.environ.get("SECRET_KEY", "giaovu-dev-secret")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _call_agent(user_message: str, vai_tro: str) -> dict:
        """
        Gọi ADK FastAPI endpoint POST /run.
        Trả về dict {"response": "...", "error": None} hoặc {"response": "", "error": "..."}
        """
        payload = json.dumps(
            {
                "message": user_message,
                "session_state": {"vai_tro": vai_tro},
            }
        ).encode("utf-8")
        url = f"{FASTAPI_URL.rstrip('/')}/chat"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                # ADK trả về nhiều định dạng tuỳ phiên bản — thử các key phổ biến
                text = (
                    body.get("response")
                    or body.get("output")
                    or body.get("text")
                    or json.dumps(body, ensure_ascii=False)
                )
                return {"response": text, "error": None}
        except urllib.error.HTTPError as exc:
            return {"response": "", "error": f"HTTP {exc.code}: {exc.reason}"}
        except Exception as exc:  # noqa: BLE001
            return {"response": "", "error": str(exc)}

    def _doc_nhat_ky() -> list[dict]:
        """Đọc file nhật ký yêu cầu CSV và trả về danh sách dict."""
        if not NHAT_KY_CSV.exists():
            return []
        rows = []
        try:
            with NHAT_KY_CSV.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(dict(row))
        except Exception:  # noqa: BLE001
            pass
        return rows

    # ── Middleware: đảm bảo vai trò trong session ────────────────────────────

    @app.before_request
    def ensure_vai_tro():
        """Nếu chưa chọn vai trò, chuyển về trang chủ để chọn (trừ static)."""
        if request.endpoint in ("chon_vai_tro", "index", "static"):
            return
        if "vai_tro" not in session:
            flash("Vui lòng chọn vai trò trước khi sử dụng.", "warning")
            return redirect(url_for("index"))

    # ── Trang chủ / chọn vai trò ─────────────────────────────────────────────

    @app.route("/", methods=["GET", "POST"])
    def index():
        """Trang chủ — chọn vai trò và hiển thị menu."""
        if request.method == "POST":
            vai_tro = request.form.get("vai_tro", "")
            if vai_tro not in VAI_TRO_LABELS:
                flash("Vai trò không hợp lệ.", "danger")
            else:
                session["vai_tro"] = vai_tro
                session["vai_tro_label"] = VAI_TRO_LABELS[vai_tro]
                flash(f"Đã đăng nhập với vai trò: {VAI_TRO_LABELS[vai_tro]}", "success")
                return redirect(url_for("tra_cuu"))
        return render_template(
            "index.html",
            vai_tro_labels=VAI_TRO_LABELS,
            current_vai_tro=session.get("vai_tro"),
        )

    @app.route("/chon-vai-tro", methods=["POST"])
    def chon_vai_tro():
        """Endpoint POST chuyên biệt để đổi vai trò từ nav."""
        vai_tro = request.form.get("vai_tro", "")
        if vai_tro in VAI_TRO_LABELS:
            session["vai_tro"] = vai_tro
            session["vai_tro_label"] = VAI_TRO_LABELS[vai_tro]
            flash(f"Đã chuyển vai trò: {VAI_TRO_LABELS[vai_tro]}", "success")
        else:
            flash("Vai trò không hợp lệ.", "danger")
        return redirect(request.referrer or url_for("index"))

    # ── Tra cứu quy chế ──────────────────────────────────────────────────────

    @app.route("/tra-cuu", methods=["GET", "POST"])
    def tra_cuu():
        """Tra cứu quy chế, quy định đào tạo — gọi agent qua ADK FastAPI."""
        ket_qua = None
        cau_hoi = ""
        error = None
        if request.method == "POST":
            cau_hoi = request.form.get("cau_hoi", "").strip()
            if cau_hoi:
                result = _call_agent(cau_hoi, session["vai_tro"])
                if result["error"]:
                    error = result["error"]
                else:
                    ket_qua = result["response"]
        return render_template(
            "tra_cuu.html",
            cau_hoi=cau_hoi,
            ket_qua=ket_qua,
            error=error,
        )

    # ── Lộ trình học lại ─────────────────────────────────────────────────────

    @app.route("/lo-trinh", methods=["GET", "POST"])
    def lo_trinh():
        """Lập lộ trình học lại / trả nợ học phần cho sinh viên."""
        ket_qua = None
        ma_sv = ""
        so_tc = 18
        xuat_bieu_mau = False
        bieu_mau_html = None
        error = None
        if request.method == "POST":
            ma_sv = request.form.get("ma_sv", "").strip()
            so_tc_raw = request.form.get("so_tc", "18").strip()
            xuat_bieu_mau = request.form.get("xuat_bieu_mau") == "1"
            try:
                so_tc = int(so_tc_raw)
            except ValueError:
                so_tc = 18
            if ma_sv:
                prompt = (
                    f"Lập lộ trình học lại cho sinh viên mã số {ma_sv}, "
                    f"tối đa {so_tc} tín chỉ mỗi kỳ."
                )
                result = _call_agent(prompt, session["vai_tro"])
                if result["error"]:
                    error = result["error"]
                else:
                    ket_qua = result["response"]
                    if xuat_bieu_mau and ket_qua:
                        prompt2 = (
                            f"Tạo biểu mẫu theo dõi lộ trình học lại cho sinh viên {ma_sv} "
                            f"dựa trên lộ trình vừa lập."
                        )
                        bm = _call_agent(prompt2, session["vai_tro"])
                        bieu_mau_html = bm.get("response") if not bm["error"] else None
        return render_template(
            "lo_trinh.html",
            ma_sv=ma_sv,
            so_tc=so_tc,
            ket_qua=ket_qua,
            bieu_mau_html=bieu_mau_html,
            error=error,
        )

    # ── Lịch & điểm ─────────────────────────────────────────────────────────

    @app.route("/lich-diem", methods=["GET", "POST"])
    def lich_diem():
        """Tra cứu lịch học và bảng điểm sinh viên."""
        ket_qua = None
        ma_sv = ""
        loai_tra_cuu = "lich"
        error = None
        if request.method == "POST":
            ma_sv = request.form.get("ma_sv", "").strip()
            loai_tra_cuu = request.form.get("loai_tra_cuu", "lich")
            if ma_sv:
                if loai_tra_cuu == "diem":
                    prompt = f"Xem bảng điểm của sinh viên mã số {ma_sv}."
                else:
                    prompt = f"Xem lịch học của sinh viên mã số {ma_sv}."
                result = _call_agent(prompt, session["vai_tro"])
                if result["error"]:
                    error = result["error"]
                else:
                    ket_qua = result["response"]
        return render_template(
            "lich_diem.html",
            ma_sv=ma_sv,
            loai_tra_cuu=loai_tra_cuu,
            ket_qua=ket_qua,
            error=error,
        )

    # ── Hàng đợi duyệt (HITL) ────────────────────────────────────────────────

    @app.route("/hang-doi", methods=["GET", "POST"])
    def hang_doi():
        """
        Hàng đợi duyệt Human-in-the-Loop.
        Trưởng phòng đào tạo phê duyệt hoặc từ chối các yêu cầu ngoài phạm vi.
        """
        ket_qua_duyet = None
        noi_dung = ""
        error = None
        if request.method == "POST":
            hanh_dong = request.form.get("hanh_dong", "")  # "duyet" hoặc "tu_choi"
            noi_dung = request.form.get("noi_dung", "").strip()
            if noi_dung:
                if session.get("vai_tro") != "truong_phong_dao_tao":
                    error = "Chỉ Trưởng phòng Đào tạo mới có quyền phê duyệt yêu cầu."
                else:
                    prompt = (
                        f"Phê duyệt HITL: {hanh_dong} — {noi_dung}"
                        if hanh_dong
                        else noi_dung
                    )
                    result = _call_agent(prompt, session["vai_tro"])
                    if result["error"]:
                        error = result["error"]
                    else:
                        ket_qua_duyet = result["response"]
        # Đọc nhật ký để hiển thị các yêu cầu cần duyệt
        nhat_ky = _doc_nhat_ky()
        # Lọc những yêu cầu ngoài phạm vi (loại = ngoai_pham_vi) chưa được xử lý
        cho_duyet = [
            row
            for row in nhat_ky
            if row.get("loai_yeu_cau", "") == "ngoai_pham_vi"
        ]
        return render_template(
            "hang_doi.html",
            cho_duyet=cho_duyet,
            ket_qua_duyet=ket_qua_duyet,
            noi_dung=noi_dung,
            error=error,
        )

    # ── Báo cáo xử lý yêu cầu ───────────────────────────────────────────────

    @app.route("/bao-cao")
    def bao_cao():
        """Báo cáo xử lý yêu cầu — đọc từ data/nhat_ky_yeu_cau.csv."""
        nhat_ky = _doc_nhat_ky()
        # Thống kê tổng quan
        tong_yeu_cau = len(nhat_ky)
        theo_loai: dict[str, int] = {}
        theo_can_bo: dict[str, int] = {}
        theo_vai_tro: dict[str, int] = {}
        for row in nhat_ky:
            loai = row.get("loai_yeu_cau", "không rõ")
            can_bo = row.get("can_bo", "không rõ")
            vai_tro = row.get("vai_tro", "không rõ")
            theo_loai[loai] = theo_loai.get(loai, 0) + 1
            theo_can_bo[can_bo] = theo_can_bo.get(can_bo, 0) + 1
            theo_vai_tro[vai_tro] = theo_vai_tro.get(vai_tro, 0) + 1
        return render_template(
            "bao_cao.html",
            nhat_ky=nhat_ky,
            tong_yeu_cau=tong_yeu_cau,
            theo_loai=theo_loai,
            theo_can_bo=theo_can_bo,
            theo_vai_tro=theo_vai_tro,
        )

    return app


# Tạo app instance để Flask CLI và Gunicorn phát hiện
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"\n  Dashboard Giáo vụ Đại Nam đang chạy tại http://0.0.0.0:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
