# ExamPlan AI - Nền Tảng Hỗ Trợ Ôn Thi Đại Học Cá Nhân Hóa Bằng AI

Hệ thống EdTech ứng dụng Trí tuệ nhân tạo (Generative AI & Spaced Repetition) giải quyết triệt để vấn đề quá tải tài liệu, thiếu định hướng và kỹ năng quản lý thời gian của sinh viên đại học.

---

## ✨ Tính Năng Cốt Lõi (Đã Hiện Thực Hóa)

1. **Đọc hiểu & Xử lý Đề cương Đa Định dạng**:
   - Tải lên tệp: **PDF**, **Word (.docx)**, **Văn bản thuần (.txt, .md)**.
   - Dán **Link URL**: Tự động cào (crawl) nội dung bài viết/giáo trình trực tuyến, làm sạch thông tin rác.
   - **Nút Thử nghiệm 1 chạm**: Nạp ngay Đề cương chuẩn đại học (Học phần *Triết học Mác - Lênin* 3 tín chỉ) để kiểm thử ngay lập tức.

2. **Bóc tách Kiến thức & Đánh giá Độ khó (AI Syllabus Analysis)**:
   - Tự động bóc tách các chương, chủ đề cốt lõi.
   - Gán nhãn độ khó khách quan: **Dễ** (Xanh), **Trung bình** (Vàng), **Khó** (Đỏ).
   - Ước tính số giờ học cần thiết cho từng chủ đề.

3. **Thuật toán Xếp Lịch Ôn Tập Ngắt Quãng (Spaced Repetition Engine)**:
   - Dựa trên đường cong quên lãng Ebbinghaus: kết hợp **Học mới** $\rightarrow$ **Ôn lặp lại (Day +2, Day +5)** $\rightarrow$ **Thi thử bấm giờ (Mock Exam)** $\rightarrow$ **Tổng ôn trước ngày thi**.
   - Tối ưu hóa theo mục tiêu điểm số của sinh viên:
     - **Qua môn (5.0 - 6.5đ)**: Tập trung 70% kiến thức trọng tâm nhất.
     - **Khá / Giỏi (7.0 - 8.0đ)**: Bao quát toàn bộ đề thi, cân đối thời gian.
     - **Xuất sắc (8.5 - 10đ)**: Ôn sâu, luyện giải đề nâng cao & thi thử.

4. **Tính Năng "Ăn Tiền": Tái Tạo Lộ Trình (Re-schedule)**:
   - Khi sinh viên bận đột xuất hoặc bị trễ bài: Chỉ cần nhấn **"⚡ Tôi Bị Lỡ Bài - Tái Tạo Lộ Trình"**, thuật toán sẽ tự động gom các bài chưa hoàn thành trong quá khứ và phân bổ lại một cách thông minh vào các ngày còn lại từ hôm nay đến ngày thi mà không làm mất kiến thức.

5. **Giao Diện Tương Tác 3 Chế Độ Xem (Dashboard EdTech)**:
   - **Lịch trình từng ngày (Daily To-Do List)**: Checkbox tick hoàn thành, cập nhật thanh tiến độ % thời gian thực, hiệu ứng pháo hoa khi hoàn thành 100%.
   - **Xem dạng Lịch tháng (Calendar Grid)**: Trực quan theo từng ô ngày.
   - **Bảng Kanban**: 3 cột *Cần Học (To-Do)* - *Ôn Lặp Lại (Recall)* - *Đã Nắm Vững (Mastered)*.

6. **Trợ Lý Gia Sư AI Hỏi Đáp Đề Cương (In-Context RAG Chatbot)**:
   - Chat trực tiếp với tài liệu đề cương đã tải lên.
   - Trả lời bám sát 100% nội dung tài liệu (chống ảo giác), có gợi ý câu hỏi mẫu nhanh.

7. **Xuất Lịch Học Ra Google Calendar**:
   - Tải file `.ics` (iCalendar) với 1 cú click để đồng bộ vào Google Calendar, Apple Calendar, hoặc Outlook trên điện thoại.

8. **Tối Ưu Chi Phí 0đ (Không tốn tiền)**:
   - Tích hợp bộ **Trích xuất Cục bộ Thông minh (Smart Local Engine)** chạy hoàn toàn offline không tốn 1 xu.
   - Hỗ trợ nhập **Google Gemini API Key Miễn phí** (15 RPM / 1M TPM từ Google AI Studio) để AI phân tích sâu hơn nếu muốn.

---

## 🚀 Hướng Dẫn Khởi Chạy Nhanh

### Bước 1: Mở Terminal tại thư mục dự án
```powershell
cd C:\Users\admin\.gemini\antigravity\scratch\exam-plan
```

### Bước 2: Chạy máy chủ
```powershell
python run_server.py
```

### Bước 3: Trải nghiệm trên trình duyệt
Mở trình duyệt và truy cập: **[http://localhost:8000](http://localhost:8000)**

---

## 📂 Cấu Trúc Thư Mục

```
exam-plan/
├── backend/
│   ├── config.py             # Cấu hình hệ thống & Gemini API
│   ├── database.py           # SQLite database & SQLAlchemy Models
│   ├── main.py               # FastAPI App & static file serving
│   ├── routes.py             # REST API endpoints (Upload, Plans, Chat, iCal)
│   └── services/
│       ├── ai_service.py     # Gemini Free API + Local Fallback Engine
│       ├── parsers.py        # Bóc tách PDF, DOCX, TXT, Web Scraper
│       ├── rag_service.py    # Chunking & Semantic Search tài liệu
│       └── scheduler.py      # Thuật toán Spaced Repetition & Rescheduling
├── data/
│   ├── uploads/              # Thư mục lưu trữ tệp đề cương
│   └── exam_plan.db          # Cơ sở dữ liệu SQLite
├── frontend/
│   ├── index.html            # Giao diện chính người dùng
│   ├── styles.css            # Tùy chỉnh hiệu ứng, glassmorphism, badges
│   └── app.js                # State management, API calls, Views rendering
├── tests/
│   ├── test_api.py           # Bộ kiểm thử tích hợp toàn bộ API
│   ├── test_parsers.py       # Kiểm thử trích xuất DOCX, TXT
│   └── test_frontend.py      # Kiểm thử serve file tĩnh
├── requirements.txt          # Danh sách thư viện Python
├── run_server.py             # Script khởi động 1-click
└── README.md                 # Tài liệu hướng dẫn sử dụng
```
