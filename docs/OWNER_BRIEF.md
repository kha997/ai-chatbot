# Kết luận dành cho Owner — Gate 0–1

Ngày 21/11/2026. Đây là nghiên cứu và thiết kế; chưa có bot/PoC hay bộ điều phối chạy thực tế.

**Khuyến nghị một phương án: LangGraph OSS làm lõi**, với lớp xác thực/phân quyền do ứng dụng kiểm soát, dữ liệu và quyền truy cập tách riêng cho NHD, HANU, ZENA. Lý do là khả năng biểu diễn rõ các bước lấy tri thức, dùng công cụ, duyệt thay đổi và quay lui để kiểm tra bằng mã. Đây là đánh giá kỹ thuật từ nguồn chính thức, chưa phải kết quả benchmark.

Langflow là phương án đối chứng thiên về thiết kế trực quan. RAGFlow, Mem0 và Chatwoot giải quyết các nhu cầu khác nhau; không nên ghép cả ba ngay từ đầu. Bắt đầu bằng truy xuất tài liệu đã duyệt, trí nhớ sở thích có cấu trúc và bàn giao nhân viên bằng mô phỏng. Chỉ thêm mô-đun khi đo được lợi ích và vượt qua kiểm thử an toàn. RAGFlow tạm loại khỏi phần chạy do còn nghi vấn về phạm vi áp dụng của một cảnh báo bảo mật.

## Kết quả bàn giao

- [So sánh năm công nghệ](OSS_DUE_DILIGENCE.md): phiên bản/commit, giấy phép, giới hạn bản thương mại, tình trạng bảo trì và cảnh báo bảo mật có nguồn.
- [Kiến trúc A/B và quyết định](ARCHITECTURE.md), [cách ly tenant và quản trị trí nhớ](SECURITY_AND_MEMORY.md).
- [Thiết kế đánh giá](EVALUATION_SPEC.md): 180 câu hỏi + các bộ bổ sung, tổng 348 kịch bản logic; có đáp án/tiêu chí, điều kiện chặn và mẫu dữ liệu giả. Chưa tạo đủ toàn bộ bộ dữ liệu, chưa chạy 348 kịch bản.
- [Widget, công cụ giả lập, chuyển nhân viên và đo chi phí](INTEGRATION_AND_OPERATIONS.md).
- [Khảo sát CLI và thiết kế Dispatcher](AGENT_DISPATCHER_DESIGN.md): Windows PATH chưa có ba CLI; WSL gọi được OpenCode 1.18.30 cho version/help. Qoder/Kilo chưa tìm thấy trên các PATH đã kiểm tra; tài khoản/chi phí và giao việc AI chưa xác minh.

**Agent thực hiện:** Codex lead và các phiên Codex riêng cho nghiên cứu nguồn, thiết kế đánh giá và phản biện. Không gán kết quả nghiên cứu cho Qoder/OpenCode/Kilo. Phiên review riêng giảm ảnh hưởng từ ngữ cảnh tác giả nhưng không phải đánh giá khác nhà cung cấp/model. Bằng chứng review và kiểm tra nằm trong [STATUS](STATUS.md) và PR.

## Điều kiện bước tiếp theo

**CONDITIONAL GO cho Gate 2 mô phỏng, nếu được phê duyệt riêng.** Gate 1 không cho phép tự bắt đầu Gate 2. Trước khi chạy: chốt bộ thư viện và kiểm tra giấy phép/cảnh báo của đúng phiên bản; hoàn thiện và đóng băng toàn bộ dữ liệu giả cùng đáp án; có cách ly quyền thật; xác định người/agent phản biện; Owner duyệt phạm vi chạy và ngân sách hữu hạn nếu dùng dịch vụ trả phí.

Chưa có số tiền/chi phí API, độ chính xác, tốc độ hay chứng nhận bảo mật được đo. Không dùng dữ liệu khách hàng, không sửa các dự án khác, không thay đổi Docker/VPS hay triển khai production. Việc xây/chạy Dispatcher cũng cần phê duyệt riêng và không phải điều kiện bắt buộc để chọn kiến trúc bot.

Rủi ro còn lại lớn nhất là cách ly khi chạy thật, giấy phép/phụ thuộc cuối cùng, chi phí mô hình và độ chính xác với tài liệu thực. [Sổ rủi ro](SECURITY_AND_MEMORY.md) quy định người phụ trách và điều kiện giải quyết. **Owner không cần quyết định thêm để hoàn tất nghiên cứu này**; quyết định tương lai chỉ là phạm vi/quyền truy cập/ngân sách Gate 2, không phải chọn framework.
