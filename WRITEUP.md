# Trợ lý Giáo vụ số Đại Nam

**Nhánh dự thi:** Agents for Good
**Người làm:** Phạm Thế An — Phòng Đào tạo, Đại học Đại Nam (anpt@dainam.edu.vn)
**Bản demo:** https://tro-ly-giao-vu-476049232437.asia-southeast1.run.app/dev-ui/?app=app
**Mã nguồn:** https://github.com/anptvnn-fta/tro-ly-giao-vu-dai-nam

---

## Short summary (English)

This is an AI assistant for academic-affairs staff at Dai Nam University, built with Google ADK 2.0 and Gemini Flash. It does two things that eat up our time today: it looks up training regulations and answers with the exact Article and Clause, and it builds a make-up/retake study plan for a student straight from their transcript, respecting prerequisites, the per-semester credit cap, and timetable clashes. Every request is role-checked, screened for prompt injection, and logged for reporting; anything out of scope is handed to a human. It runs live on Cloud Run. For me this isn't a class exercise — it's the working prototype for a real initiative I'm running at the university from August 2026 to June 2027.

---

## Vì sao tôi làm cái này

Tôi làm ở Phòng Đào tạo. Có hai việc lặp đi lặp lại mỗi ngày mà tôi muốn bớt cực:

Thứ nhất là **tra cứu quy chế**. Quy định về học lại, học cải thiện, trả nợ học phần, cảnh báo học vụ, điều kiện tốt nghiệp… nằm rải rác trong nhiều file Word, PDF. Mỗi lần sinh viên hỏi một câu, tôi phải mở vài văn bản tìm đúng điều khoản, mất chừng mười lăm phút. Tệ hơn là hai người trả lời có khi không giống nhau vì xem nhầm bản cũ.

Thứ hai là **tư vấn lộ trình học lại**. Khi một em nợ nhiều môn, tôi phải ngồi đối chiếu bảng điểm, chương trình đào tạo, điều kiện tiên quyết và lịch mở lớp để xếp xem em nên học lại môn nào trước, môn nào sau, mỗi kỳ bao nhiêu tín. Việc này dễ sai, nhất là khi môn này là tiên quyết của môn kia, hoặc hai lớp trùng giờ.

Tôi muốn một trợ lý làm giúp hai việc đó, nhưng phải **trả lời có dẫn nguồn** (không bịa), **có phân quyền** (cán bộ tra cứu thường không được xem điểm chi tiết của sinh viên), và **ghi lại mọi yêu cầu** để cuối tháng có cái mà báo cáo.

---

## Nó làm được gì

Người dùng là cán bộ giáo vụ. Họ gõ một câu bằng tiếng Việt bình thường, agent tự hiểu thuộc loại nào rồi xử lý:

- **Tra cứu quy chế.** Hỏi "Sinh viên bị điểm F có phải học lại không, điều kiện gì?" thì nó trả lời dựa trên văn bản và dẫn rõ *[Điều 5, Khoản 2]*. Nếu trong tài liệu không có thì nó nói không tìm thấy, chứ không bịa.
- **Lập lộ trình học lại / trả nợ học phần.** Nhập mã sinh viên là nó đọc bảng điểm, lọc ra môn còn nợ thật (môn nào học lại đã đậu thì bỏ qua), sắp theo điều kiện tiên quyết, chia vào từng kỳ sao cho không vượt số tín chỉ tối đa và cảnh báo nếu trùng lịch.
- **Tra cứu lịch học và bảng điểm** theo mã sinh viên.
- **Sinh biểu mẫu** theo dõi (ví dụ kế hoạch học lại).
- **Việc ngoài phạm vi** (kiểu xét miễn giảm học phí diện chính sách) thì nó không tự quyết, mà đẩy lên hàng đợi để trưởng phòng duyệt.

Mọi yêu cầu đều được ghi vào một file nhật ký, và có một trang **Báo cáo** tổng hợp lại — đúng cái sản phẩm "báo cáo xử lý yêu cầu" mà sáng kiến của tôi cần.

---

## Bên trong nó chạy thế nào

Tôi dùng đồ thị workflow của ADK 2.0. Hình dung đơn giản: một câu hỏi đi vào, qua một bước phân loại, rồi rẽ về đúng "chuyên viên" lo việc đó.

```
Câu hỏi của cán bộ
      │
      ▼
   intake            → phân loại: tra cứu quy chế / lộ trình học lại /
   (LlmAgent)          lịch-điểm / sinh biểu mẫu / ngoài phạm vi
      │                (đồng thời chép nguyên văn câu hỏi để bước sau dùng)
      ▼
   route             → rẽ nhánh theo loại
      │
      ├── reg_lookup     → tra cứu quy chế, trả lời kèm [Điều, Khoản]
      ├── path_planner   → lập lộ trình học lại (đọc điểm + CTĐT + lịch)
      ├── lich_diem      → tra lịch học / bảng điểm
      ├── form_filler    → sinh biểu mẫu
      └── escalate       → đẩy lên hàng đợi cho người duyệt (HITL)
```

Bao quanh đồ thị là một lớp an toàn (`SafetyPlugin`) với ba chốt: chặn prompt injection ở đầu vào, che thông tin cá nhân ở đầu ra, và kiểm tra quyền trước mỗi lần gọi công cụ. Phần lập lộ trình là một hàm Python thuần (sắp xếp tô-pô theo môn tiên quyết, dồn vào từng kỳ theo trần tín chỉ), nên nó chạy chắc chắn và kiểm thử được, không phụ thuộc may rủi của mô hình.

Bản web cho cán bộ là một dashboard Flask đơn giản, gọi sang agent qua endpoint `/chat`, có các trang: tra cứu, lộ trình, lịch & điểm, hàng đợi duyệt, và báo cáo.

### Khóa học dùng ở đâu trong dự án

Mỗi ngày của khóa học đều nằm trong dự án ở một chỗ cụ thể:

- **Day 1 (Agent & điều phối):** agent = mô hình + công cụ + điều phối + triển khai; đồ thị `intake → route → các chuyên viên` chính là mẫu router/coordinator; nhánh `escalate` là human-in-the-loop.
- **Day 2 (Công cụ):** tám công cụ trong `app/tools.py`, mỗi cái có kiểu tham số rõ ràng, docstring, và `ToolContext`; công cụ trả về JSON gọn (ví dụ tra cứu quy chế trả về đoạn văn + nguồn) chứ không đổ dữ liệu thô vào ngữ cảnh.
- **Day 3 (Ngữ cảnh & bộ nhớ):** dùng session/state để truyền kết quả phân loại qua các bước (`output_key="phan_loai"`), và vai trò người dùng lưu trong `session.state["vai_tro"]` để kiểm soát truy cập.
- **Day 4 (Chất lượng & an toàn):** `SafetyPlugin` với ba callback; bộ eval 20 ca + script chấm điểm; câu chuyện vòng lặp chất lượng ở dưới.
- **Day 5 (Triển khai):** đóng gói FastAPI, deploy lên Cloud Run, có dashboard cho con người và ghi log/observability.

---

## Tôi kiểm tra chất lượng ra sao

Tôi viết một bộ 20 câu hỏi mẫu (`tests/eval/datasets/giaovu-dataset.json`): 7 câu tra cứu quy chế, 5 câu lộ trình học lại, 3 câu lịch/điểm, 2 câu ngoài phạm vi, và 3 câu cố tình tấn công. Rồi tôi cho agent chạy hết 20 câu và chấm bằng mấy thước đo tự viết.

Điều thú vị là **bộ eval đã bắt được một lỗi thật mà tôi không thấy khi bấm thử bằng tay**. Lần chấm đầu, chỉ số "có trích dẫn" của phần tra cứu quy chế là **0%** — agent toàn trả lời chung chung kiểu "bạn cần hỏi gì". Lần theo vết, tôi phát hiện node tra cứu chỉ nhận được kết quả phân loại của bước trước, chứ không thấy câu hỏi gốc, nên nó tìm kiếm bằng từ khóa vu vơ. Tôi sửa lại cho câu hỏi gốc được chép sang bước sau. Chấm lại:

| Thước đo | Trước khi sửa | Sau khi sửa |
|---|---|---|
| Tra cứu có trích dẫn Điều/Khoản | 0% | **64%** (7/11 câu) |
| Từ chối đúng khi ngoài phạm vi / bị tấn công | 80% | **80%** (4/5 câu) |
| Chạy trọn 20 câu không lỗi | — | **20/20** |

Đây đúng là cái "vòng lặp chất lượng" mà Day 4 nói: đo được thì mới thấy lỗi, sửa rồi đo lại thấy tốt lên. Mỗi lần cán bộ chỉnh tay một kết quả ở hàng đợi duyệt, ca đó cũng thành một ca kiểm thử mới cho lần sau.

Phần **phân quyền** thì tôi kiểm bằng **65 unit test** (`tests/unit/`), vì bộ eval chạy mọi câu với cùng một vai trò mặc định nên không tiện đổi vai trò theo từng câu. Các test khẳng định: tra cứu viên không xem được hồ sơ/điểm sinh viên, cán bộ giáo vụ không duyệt được hàng đợi, còn trưởng phòng thì toàn quyền.

Một lưu ý thật thà: bước chấm điểm tự động của `agents-cli` chạy qua dịch vụ Vertex AI, mà project GCP của tôi mới bật nên Google chưa cấp xong tài khoản dịch vụ (báo lỗi 404 "Gaia id not found"). Thay vì ngồi chờ, tôi viết luôn một script `tests/eval/cham_diem_offline.py` tính ba thước đo trực tiếp từ file traces — không cần Vertex, chạy ở máy nào cũng ra cùng một số. Cách này hóa ra lại tiện hơn cho người chấm muốn tái lập kết quả.

---

## An toàn và phân quyền

Có ba vai trò: *tra cứu viên* (chỉ tra quy chế), *cán bộ giáo vụ* (tra cứu + lập lộ trình + lịch/điểm + biểu mẫu), và *trưởng phòng đào tạo* (toàn quyền, duyệt hàng đợi). Quyền được kiểm ở hai nơi cho chắc: trong từng công cụ, và ở callback `before_tool_callback` trước khi công cụ chạy.

Ngoài ra, đầu vào được quét tìm dấu hiệu prompt injection (cả tiếng Việt lẫn tiếng Anh — kiểu "bỏ qua hướng dẫn", "ignore previous instructions"), và đầu ra được che mã sinh viên, email, số điện thoại với những vai trò không đủ quyền. Tôi đã chạy thử trực tiếp: câu tấn công bị chặn, còn câu hỏi bình thường vẫn qua.

---

## Triển khai

Dự án chạy được theo hai đường: chỉ với một API key của Google AI Studio (đủ cho demo, không cần bật billing nặng), hoặc đầy đủ trên Google Cloud. Bản demo đang chạy thật trên Cloud Run, khu vực Singapore (asia-southeast1):

```bash
gcloud run deploy tro-ly-giao-vu --source . --region asia-southeast1 \
  --allow-unauthenticated --memory 1Gi \
  --set-env-vars "GOOGLE_API_KEY=...,GOOGLE_GENAI_USE_VERTEXAI=FALSE"
```

Container không giữ trạng thái, cổng lấy từ biến môi trường, dữ liệu mẫu nằm trong ảnh. Khi lên thật thì phần dữ liệu sinh viên và nhật ký nên chuyển sang cơ sở dữ liệu ngoài.

---

## Liên hệ với công việc thật của tôi

Cái này không dừng ở bài nộp. Nó là bản thí điểm cho một sáng kiến tôi phụ trách ở Đại học Đại Nam, dự kiến chạy từ **tháng 8/2026 đến tháng 6/2027**: số hóa quy chế, dựng biểu mẫu theo dõi, và thử nghiệm trợ lý tra cứu có phân quyền cho phòng Đào tạo. Mục tiêu rất cụ thể — giảm thời gian xử lý mỗi yêu cầu, và giảm sai sót khi tư vấn lộ trình học lại, trả nợ học phần.

Lộ trình tôi hình dung: tháng 8–9 số hóa quy chế và nhập dữ liệu thật; tháng 10–12 cho một hai cán bộ dùng thử và thu nhật ký; đầu 2027 chạy vòng cải thiện dựa trên nhật ký đó; rồi mở ra cả phòng.

---

## Những chỗ chưa hoàn hảo, và sẽ làm tiếp

Tôi muốn nói thẳng vài hạn chế:

- Phần tra cứu hiện tìm theo từ khóa đơn giản, đạt 64% có trích dẫn — đủ tốt cho prototype nhưng sẽ khá hơn nhiều nếu thay bằng tìm kiếm theo embedding và quy chế đầy đủ (giờ tôi mới đưa vào vài văn bản mẫu).
- Dữ liệu sinh viên đang là dữ liệu giả để demo. Khi triển khai thật phải dùng dữ liệu thật (đã ẩn danh) và chuyển sang cơ sở dữ liệu có sao lưu.
- Việc chấm điểm bằng "LLM làm giám khảo" tôi để lại làm bước sau, khi tài khoản Vertex AI sẵn sàng.

Nhưng phần lõi — hiểu yêu cầu, tra cứu có dẫn nguồn, lập lộ trình đúng tiên quyết và tín chỉ, phân quyền, ghi nhật ký, và chạy thật trên cloud — thì đã hoạt động.

---

## Liên kết

- **Bản demo (Cloud Run):** https://tro-ly-giao-vu-476049232437.asia-southeast1.run.app/dev-ui/?app=app
- **Mã nguồn (GitHub):** https://github.com/anptvnn-fta/tro-ly-giao-vu-dai-nam
- **Video demo:** https://youtu.be/oKD2YVfJV5E
