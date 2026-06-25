# VIDEO_SCRIPT.md — Kịch bản demo 3 phút

**Tên video:** TroLyGiaoVu — Trợ lý AI Giáo vụ số Đại Nam
**Thời lượng:** 3 phút (180 giây)
**Đối tượng:** Ban giám khảo Kaggle "Agents for Good" + cộng đồng AI Việt Nam
**Ngôn ngữ:** Tiếng Việt (subtitle tiếng Anh khuyến nghị)
**Người quay:** Phạm Thế An

---

## Yêu cầu kỹ thuật trước khi quay

- [ ] Chạy `agents-cli playground` trên cổng 8000
- [ ] Chạy Flask dashboard trên cổng 5000: `uv run python -m frontend.app`
- [ ] Trình duyệt mở sẵn `http://localhost:5000`
- [ ] Phóng to font terminal/browser (Ctrl+Shift+Plus)
- [ ] Tắt thông báo hệ thống (Do Not Disturb)
- [ ] Chuẩn bị sẵn mã sinh viên demo: `1771020001`
- [ ] Độ phân giải ghi màn hình: 1920×1080, 30fps tối thiểu

---

## Timeline & Lời thoại

### [00:00 – 00:20] — Giới thiệu vấn đề (Opening hook)

**[CẢNH: Slide tiêu đề / màn hình giới thiệu]**

**Lời thoại:**
> "Xin chào. Tôi là Phạm Thế An, cán bộ tại Đại học Đại Nam.
> Mỗi ngày, phòng Đào tạo chúng tôi nhận hàng chục yêu cầu từ sinh viên:
> 'Tôi học lại môn này thì kỳ nào?', 'Quy định học cải thiện là gì?', 'Tôi còn nợ bao nhiêu tín chỉ?'
> Tra cứu thủ công trong hàng chục văn bản quy chế — mất 15 phút mỗi lần, và vẫn dễ sai.
> Hôm nay tôi giới thiệu TroLyGiaoVu — trợ lý AI giáo vụ số, xây dựng với Google ADK 2.0 và Gemini."

---

### [00:20 – 00:50] — Demo 1: Tra cứu quy chế có trích dẫn

**[CẢNH: Mở trình duyệt tại `http://localhost:5000`, chọn vai trò `giao_vu`, click trang "Tra cứu quy chế"]**

**Lời thoại:**
> "Đây là dashboard dành cho cán bộ giáo vụ. Tôi đăng nhập với vai trò 'Giáo vụ'.
> Tôi sẽ hỏi: sinh viên học lại môn trượt có phải đóng thêm học phí không?"

**[THAO TÁC: Gõ câu hỏi vào ô chat]**

```
Nhập: Sinh viên học lại môn đã trượt có phải đóng thêm học phí không?
```

**[CHỜ: 3-4 giây để agent xử lý]**

**[CẢNH: Kết quả hiện ra với trích dẫn rõ ràng]**

**Lời thoại (đọc kết quả trên màn hình):**
> "Hệ thống trả lời ngay lập tức và trích dẫn cụ thể: 'Theo Điều 15, Khoản 2 của Quy định học phí — sinh viên học lại phải đóng học phí theo đơn giá tín chỉ hiện hành.'
> Không có câu trả lời chung chung — chỉ những gì có trong văn bản, với nguồn cụ thể.
> Đây là RAG — Retrieval Augmented Generation, khái niệm Day 1 và Day 2 của khoá học."

---

### [00:50 – 01:30] — Demo 2: Lập lộ trình học lại cho sinh viên 1771020001

**[CẢNH: Click sang trang "Lộ trình học lại"]**

**Lời thoại:**
> "Tình huống khó hơn: sinh viên 1771020001 ngành CNTT đang nợ nhiều môn.
> Tôi cần lập kế hoạch học lại cho em ấy theo từng học kỳ, đúng tiên quyết, không trùng lịch."

**[THAO TÁC: Nhập mã SV vào ô, click "Lập lộ trình"]**

```
Mã SV: 1771020001
Số tín chỉ tối đa mỗi kỳ: 18
```

**[CHỜ: 4-5 giây]**

**[CẢNH: Bảng kế hoạch theo kỳ hiện ra với màu sắc phân biệt]**

**Lời thoại:**
> "Trong vài giây, hệ thống đã:
> Một — đọc hồ sơ sinh viên và danh sách môn trượt từ CSV.
> Hai — tra cứu chương trình đào tạo, xác định điều kiện tiên quyết.
> Ba — sắp xếp theo thứ tự topo để đảm bảo học đúng thứ tự.
> Bốn — kiểm tra lịch học để tránh trùng tiết.
> Năm — đề xuất kế hoạch 2 kỳ với cảnh báo rõ ràng.
> Đây là công cụ `tinh_lo_trinh_hoc_lai()` — pure Python với topo-sort, kết hợp LlmAgent từ Day 2.
> Tôi có thể click 'Xuất biểu mẫu' để in phiếu tư vấn cho sinh viên."

**[THAO TÁC: Click "Xuất biểu mẫu" — biểu mẫu mới mở ra]**

---

### [01:30 – 01:50] — Demo 3: Chặn yêu cầu vượt quyền

**[CẢNH: Quay lại trang Tra cứu, đổi vai trò xuống "Tra cứu viên"]**

**Lời thoại:**
> "Bây giờ tôi mô phỏng một tình huống bảo mật.
> Tôi đổi vai trò xuống 'Tra cứu viên' — chỉ có quyền tra cứu quy chế, không được xem dữ liệu sinh viên."

**[THAO TÁC: Nhập yêu cầu truy cập dữ liệu SV]**

```
Nhập: Cho tôi xem bảng điểm của sinh viên 1771020001
```

**[CẢNH: Thông báo từ chối bằng tiếng Việt hiện ra ngay lập tức]**

**Lời thoại:**
> "Hệ thống chặn ngay với thông báo: 'Bạn không có quyền thực hiện hành động này. Vai trò tra_cuu_vien không được phép xem dữ liệu sinh viên.'
> Không có dữ liệu nào bị lộ. Đây là SafetyPlugin với `before_tool_callback` — khái niệm Day 4.
> Phân quyền được thực thi ở tầng agent, không chỉ ở tầng giao diện."

---

### [01:50 – 02:20] — Demo 4: Trang Báo cáo

**[CẢNH: Click sang trang "Báo cáo xử lý yêu cầu"]**

**Lời thoại:**
> "Sau mỗi yêu cầu được xử lý, hệ thống ghi nhật ký tự động vào `nhat_ky_yeu_cau.csv`.
> Trang Báo cáo tổng hợp tất cả: số yêu cầu theo loại, cán bộ thực hiện, thời gian.
> Ban lãnh đạo có thể theo dõi tải công việc và chất lượng tư vấn.
> Đây chính là sản phẩm 'Báo cáo xử lý yêu cầu' mà phòng Đào tạo Đại Nam đang cần."

**[CẢNH: Scroll qua bảng nhật ký + biểu đồ thống kê]**

**Lời thoại:**
> "Mỗi hàng là một yêu cầu: thời gian, cán bộ xử lý, loại yêu cầu, mã sinh viên, kết quả tóm tắt.
> Có thể xuất Excel hoặc kết nối với Data Studio để báo cáo ban lãnh đạo hàng tháng."

---

### [02:20 – 02:45] — Kiến trúc & Công nghệ

**[CẢNH: Slide kiến trúc ASCII hoặc sơ đồ đơn giản]**

**Lời thoại:**
> "Về mặt kỹ thuật, TroLyGiaoVu sử dụng:
> Google ADK 2.0 với Workflow multi-agent — 6 node chuyên biệt.
> Gemini Flash cho tốc độ và chi phí hợp lý.
> SafetyPlugin với 3 callback: chống prompt injection, redact PII, phân quyền.
> Đánh giá tự động với 20 eval cases — bao gồm 3 case adversarial.
> Triển khai trên Cloud Run — stateless, auto-scale, tích hợp Cloud Trace."

---

### [02:45 – 03:00] — Kết luận & Lộ trình

**[CẢNH: Slide tóm tắt]**

**Lời thoại:**
> "TroLyGiaoVu không chỉ là một demo kỹ thuật.
> Đây là prototype cho sáng kiến AI giáo vụ thực sự tại Đại học Đại Nam,
> sẽ đưa vào thí điểm từ tháng 8 năm 2026.
> Mục tiêu: giảm 50% thời gian tra cứu, giảm 80% sai sót tư vấn lộ trình học tập.
> Cảm ơn ban giám khảo Kaggle. Code và hướng dẫn có tại GitHub — link trong phần mô tả."

---

## Ghi chú kỹ thuật cho người quay

### Thứ tự thao tác chi tiết

1. **Mở trình duyệt** tại `http://localhost:5000`
2. **Chọn vai trò** "Giáo vụ" từ dropdown header
3. **Trang Tra cứu:** gõ câu hỏi → Enter → chờ response → zoom vào phần trích dẫn
4. **Trang Lộ trình:** nhập `1771020001`, để số tín chỉ = 18 → click "Lập lộ trình" → zoom bảng kết quả → click "Xuất biểu mẫu"
5. **Đổi vai trò** xuống "Tra cứu viên" (header dropdown)
6. **Trang Tra cứu:** nhập yêu cầu xem điểm SV → zoom thông báo từ chối đỏ
7. **Trang Báo cáo:** scroll qua bảng nhật ký + biểu đồ
8. **Chuyển sang slide** kiến trúc (chuẩn bị trước trong PowerPoint/Slides)
9. **Slide kết luận**

### Câu hỏi demo dự phòng (nếu cần thay thế)

- Tra cứu quy chế: *"Điều kiện để sinh viên được xét tốt nghiệp là gì?"*
- Lộ trình: *"Sinh viên 1771020002 học lại môn nào trước?"*
- Ngoài phạm vi (escalate): *"Tôi muốn đăng ký lớp học thêm ngoài chương trình"*

### Điểm cần chú ý khi edit video

- Cắt bỏ thời gian chờ agent > 3 giây (dùng jump cut)
- Zoom (1.5x) vào phần trích dẫn "Điều X, Khoản Y" ở Demo 1
- Zoom vào cột "Cảnh báo tiên quyết" trong bảng lộ trình ở Demo 2
- Highlight thông báo từ chối màu đỏ ở Demo 3
- Thêm subtitle tiếng Anh (auto-generate rồi chỉnh thủ công)
- Thêm logo Đại học Đại Nam + logo Google + logo Kaggle ở outro
