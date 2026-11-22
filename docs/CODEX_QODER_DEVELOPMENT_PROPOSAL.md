# Đề xuất phát triển Codex và Qoder

**Chờ Owner quyết định.** Rà soát `main` tại `720a30ae25bc3a485c5d422e95edf17971d5b73a`. Kho mã có hợp đồng báo giá và chuyển tiếp, ba ca báo giá giả lập và các công cụ kiểm thử kỹ thuật. Chưa có ứng dụng chatbot chạy cho người dùng. Watcher hiện có chỉ đọc và phân loại công việc GitHub. [Kiến trúc](ARCHITECTURE.md) · [Hợp đồng tích hợp](INTEGRATION_AND_OPERATIONS.md) · [Ba ca hiện có](../eval/examples.json).

## Ưu tiên đầu tiên

**Kiểm tra báo giá nháp có nguồn cho NHD, HANU và ZENA bằng dữ liệu giả lập.** Đây là một phần nhỏ dùng lại được của luồng báo giá, kiểm chứng được số tiền và nguồn mà không cần model hay dịch vụ. Dùng lại ba ca hiện có làm mốc, với kết quả lần lượt là 600.000, 50.000 và 600.000 VND. Phần xác minh chạy bằng Python chuẩn trên các fixture, tách khỏi widget, provider và mạng.

| Nhiệm vụ | Người thực hiện | Review độc lập | Kiểm thử và PR |
| --- | --- | --- | --- |
| Bổ sung ca chấp nhận báo giá | Qoder, sau khi xác minh quyền và giới hạn sử dụng. Chỉ làm việc với fixture giả lập trong `eval/`. | Codex lead đối chiếu từng kết quả với nguồn, kiểm tra ca từ chối có đủ thông tin để chạy lại. | PR 1 chỉ chứa fixture và mô tả kết quả mong đợi. Kiểm tra JSON, ID không trùng, số tiền và nguồn của ba ca hiện có, tài liệu sai tenant, tài liệu hết hiệu lực, mục không tồn tại và số lượng không hợp lệ. |
| Kiểm tra báo giá nháp bằng Python | Codex lead viết logic xác định nhỏ và unit test sau khi hợp đồng fixture được review. Nhận tenant từ ngữ cảnh giả lập đã gắn sẵn. | Một phiên Codex riêng không viết mã hoặc oracle kiểm tra từ commit/diff đóng băng. | PR 2 dùng Python `Decimal` và `unittest`. Ba ca đúng phải khớp số tiền, tiền tệ và nguồn. Ca chéo tenant hoặc nguồn không hợp lệ phải từ chối hay yêu cầu làm rõ theo oracle, không xuất số tiền hoặc nguồn sai. Không phát sinh tác dụng phụ. |

Mỗi PR có một người viết, branch và worktree riêng. Ghi rõ commit nền, lệnh chạy, kết quả thật và người review. Giao việc thủ công bằng GitHub Issue/PR với nhãn `agent:codex` hoặc `agent:qoder`, dùng watcher hiện có để theo dõi. Chỉ merge khi kiểm thử và review độc lập đạt. Kết quả chỉ chứng minh hợp đồng và phép tính trên fixture, chưa chứng minh phân quyền hay chất lượng trả lời của chatbot khi chạy thật. [Quy chế phối hợp](MULTI_AGENT_OPERATING_MODEL.md) · [Watcher](GITHUB_WATCHER_DESIGN.md).

Lần đánh giá trước chưa xác minh được chặn phát sinh phí và ranh giới cách ly cho Qoder CLI. Chỉ giao phần việc cho Qoder khi xác nhận được chế độ sử dụng thuộc phạm vi được phép và có ranh giới dữ liệu phù hợp. Nếu chưa đạt, Codex có thể chuẩn bị fixture trong một phiên riêng và ghi rõ Qoder chưa tham gia. Không khởi chạy Qoder tự động, phát sinh chi phí ngoài quyền đã duyệt hoặc đưa dữ liệu thật vào tác vụ. [Biên nhận quyền và cách ly Qoder](AGENT_PIVOT_28.md).

**Quyết định đề xuất:** duyệt hai PR của đợt báo giá giả lập. Sau đợt này có thể áp dụng cùng cách kiểm tra cho chuyển tiếp hỗ trợ. Hướng Ollama, kiểm tra tài nguyên và SDK mock vẫn tạm dừng. Agent Dispatcher, Gate 2 và production tiếp tục **NO-GO**.
