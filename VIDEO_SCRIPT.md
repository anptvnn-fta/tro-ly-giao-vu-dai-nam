# Kịch bản video demo (khoảng 3 phút)

Mục tiêu: quay nhanh, gọn, và **chỉ demo những thứ chắc chắn chạy**. Phần lõi quay
thẳng trên bản đang chạy thật ở Cloud Run, nên không sợ lỗi lúc ghi hình.

- **Bản demo:** https://tro-ly-giao-vu-476049232437.asia-southeast1.run.app/dev-ui/?app=app
- **Mã sinh viên mẫu:** 1771020001
- Quay màn hình 1080p, phóng to chữ một chút, tắt thông báo hệ thống.

---

## Chuẩn bị (làm trước khi bấm ghi)

- Mở sẵn link demo ở trên, chọn agent **app** trong danh sách bên trái.
- Mở sẵn một cửa sổ terminal tại thư mục dự án (để chạy script chấm điểm và test).
- Nếu muốn quay thêm dashboard cán bộ (phần tùy chọn ở cuối), chạy trước:
  `uvicorn app.fast_api_app:app --port 8000` và `FASTAPI_URL=http://localhost:8000 flask --app frontend.app run --port 5000`.

---

## Lời mở đầu — khoảng 0:00–0:25

Nói thẳng vào vấn đề, giọng tự nhiên như đang kể:

> "Mình là Phạm Thế An, làm ở Phòng Đào tạo trường Đại học Đại Nam. Mỗi ngày tụi mình
> mất rất nhiều thời gian cho hai việc: tra cứu quy chế cho sinh viên, và xếp lộ trình
> học lại cho mấy bạn nợ môn. Hai việc đó dễ sai và tốn thời gian. Nên mình làm một trợ
> lý AI để lo giúp — đây là nó, đang chạy thật trên Cloud Run."

---

## Demo 1 — Tra cứu quy chế có dẫn nguồn — khoảng 0:25–1:00

Gõ vào ô chat của dev-ui:

> Sinh viên bị điểm F có phải học lại không? Điều kiện gì?

Chờ vài giây. Khi câu trả lời hiện ra (có dẫn **[Điều 5, Khoản 2]**), nói:

> "Để ý là nó không trả lời chung chung. Nó dựa đúng vào văn bản quy chế và dẫn rõ Điều,
> Khoản. Nếu trong tài liệu không có thì nó nói không tìm thấy chứ không bịa. Bên trái là
> các bước nó chạy: phân loại câu hỏi, rồi gọi công cụ tra cứu quy chế."

Mẹo: bấm vào tab Events/Trace bên trái để khán giả thấy luồng `intake → tra_cuu_quy_che`.

---

## Demo 2 — Lập lộ trình học lại — khoảng 1:00–1:40

Gõ tiếp:

> Lập lộ trình học lại cho sinh viên 1771020001, tối đa 12 tín chỉ mỗi kỳ.

Chờ nó chạy, rồi nói khi kết quả hiện ra:

> "Đây là phần mình tâm đắc nhất. Chỉ từ mã sinh viên, nó đọc bảng điểm, lọc ra đúng những
> môn còn nợ — mấy môn học lại đã đậu thì nó bỏ qua — rồi xếp thành ba kỳ, đảm bảo môn tiên
> quyết học trước, mỗi kỳ không quá mười hai tín, và cảnh báo nếu trùng lịch. Cái này nếu
> làm tay thì mất cả buổi và rất dễ sót."

Chỉ vào phần các bước bên trái: `lay_ho_so_sinh_vien → tinh_lo_trinh_hoc_lai`.

---

## Demo 3 — Việc ngoài phạm vi thì không tự quyết — khoảng 1:40–1:55

Gõ một câu lạc đề:

> Hôm nay Hà Nội thời tiết thế nào?

Khi nó từ chối lịch sự và báo chuyển cho cán bộ, nói:

> "Gặp việc ngoài phạm vi, nó không bịa câu trả lời. Nó từ chối nhẹ nhàng và đẩy lên hàng
> đợi để người có thẩm quyền xem — đúng tinh thần có con người trong vòng lặp."

---

## Demo 4 — Chất lượng được đo, lỗi được sửa — khoảng 1:55–2:25

Chuyển sang cửa sổ terminal, chạy:

> python tests/eval/cham_diem_offline.py

Khi bảng điểm hiện ra (tra cứu có trích dẫn 64%, từ chối đúng 80%), nói:

> "Mình không chỉ làm cho chạy, mà còn đo. Mình có hai mươi câu hỏi mẫu để chấm. Thú vị là
> lần chấm đầu, điểm tra cứu là 0% — nó toàn trả lời chung chung. Nhờ đo mới phát hiện một
> node không nhận được câu hỏi gốc. Mình sửa, chấm lại, lên 64%. Đo được thì mới sửa được."

Có thể chạy thêm để khoe phần phân quyền được kiểm bằng test:

> uv run pytest tests/unit -q

Nói: "Phân quyền — ai được xem gì — mình kiểm bằng 65 unit test, tất cả đều đậu."

---

## Demo 5 (tùy chọn) — Dashboard cán bộ và trang Báo cáo — khoảng 2:25–2:45

*Chỉ quay phần này nếu đã chạy được dashboard Flask ở bước chuẩn bị.* Mở
`http://localhost:5000`, chọn vai trò, vào trang **Báo cáo**:

> "Đây là bản web cho cán bộ. Mọi yêu cầu đều được ghi nhật ký, và trang Báo cáo tổng hợp
> lại để cuối tháng có cái trình lãnh đạo — đúng sản phẩm mà sáng kiến của mình cần."

Nếu dashboard chưa sẵn sàng thì bỏ qua, không sao — bốn demo trên là đủ.

---

## Kết — khoảng 2:45–3:00

> "Cái này với mình không phải bài tập. Nó là bản thí điểm cho một việc thật mình đang phụ
> trách ở trường, chạy từ tháng 8 năm nay tới giữa năm sau. Mục tiêu đơn giản: bớt thời gian,
> bớt sai sót cho công tác giáo vụ. Cảm ơn mọi người đã xem. Mã nguồn và link demo mình để ở
> phần mô tả."

---

## Vài lưu ý khi dựng

- Câu nào agent chạy lâu quá vài giây thì cắt bớt cho gọn (jump cut).
- Phóng to vào chỗ trích dẫn "[Điều 5, Khoản 2]" ở Demo 1 và bảng lộ trình ở Demo 2.
- Nếu muốn có phụ đề tiếng Anh thì bật auto-caption rồi sửa lại vài chỗ.
- Nhớ dùng dữ liệu mẫu (sinh viên giả) — không quay dữ liệu thật của sinh viên nào.
