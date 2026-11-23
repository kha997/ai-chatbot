# Hồ sơ chuẩn bị thử nghiệm AI giả lập — Issue #61

Ngày: **23/11/2026**. [PR #62](https://github.com/kha997/ai-chatbot/pull/62) · [Phạm vi và bằng chứng](GATE_A_PREPARATION_61.md). Baseline là PR #60 đã merge tại `24d8fb46f7726e42bcce4bb48904e6f8738250d7`.

## Khuyến nghị và giới hạn

**Chỉ nghiệm thu hồ sơ chuẩn bị; chưa cho phép chạy thử AI.** Giữ đề xuất GPT-5.4 mini bản `2026-03-17`, luồng xử lý đơn giản và bộ tính báo giá xác định. Tài liệu này không tự cấp ngân sách 10 USD, không kích hoạt 600 request, không triển khai Gate 2 và không cho dùng dữ liệu thật. Không tự merge trước Architecture Acceptance.

Đã thiết kế danh mục 60 câu hỏi chấm điểm (mỗi câu hai lượt), 12 ca phát triển, 24 ca tấn công và 12 hành trình hội thoại/chuyển nhân viên giả lập. **Chưa có 60 câu hỏi với đáp án độc lập sẵn sàng chạy**: dữ liệu hiện tại chỉ có một mã hàng NHD giả lập. Lặp cách hỏi hoặc thay số lượng không chứng minh hiểu nhiều loại hàng. Bộ dữ liệu/đáp án mở rộng phải được tác giả và người review độc lập chuẩn bị trong phạm vi được cho phép riêng sau này. [Danh mục và cách chấm](GATE_A_CORPUS_61.md).

## Những biện pháp đã thiết kế

- Chỉ gửi các trường văn bản giả lập/công khai đã được duyệt và chốt nội dung; chặn thông tin cá nhân, dữ liệu kinh doanh thật, tài liệu riêng, file đính kèm và liên kết lạ trước cả bước gọi model. Model không được tự cấp quyền, tạo đơn, đồng ý chia sẻ hoặc chuyển dữ liệu cho nhân viên. [Chính sách dữ liệu](GATE_A_CONTROLS_61.md).
- Chấm đúng/sai theo nguồn và quyền truy cập, không chỉ độ trôi chảy. Mỗi lượt cần ít nhất 54/60 câu đúng, mỗi nhóm ít nhất 5/6; lỗi rò rỉ tenant, sai giá/nguồn/quyền/đồng ý hay tự nâng chat thành chính sách đều chặn nghiệm thu dù điểm trung bình cao. PASS nghĩa là đạt đủ tiêu chí; FAIL là không đạt; STOP là dừng gửi thêm request; INCONCLUSIVE là chưa đủ bằng chứng để kết luận; NOT_RUN là chưa chạy.
- Trước mỗi request phải giữ chỗ chi phí tối đa, kể cả request đang chạy, lỗi và retry. Đề xuất dừng nhận request ở 8 USD, giữ 2 USD dự phòng trong trần 10 USD; tối đa 600 request tổng, tối đa 5 đang chạy, không retry tự động hay tự đổi provider. Mỗi lần thử lại vẫn tốn một suất trong tổng 600 và quỹ dự phòng tối đa 64 request, không xóa kết quả lỗi ban đầu. Giá/mức sử dụng không xác định thì dừng. [Ngân sách và xử lý lỗi](GATE_A_BUDGET_61.md).

Theo giá công khai đã kiểm tra ngày 23/11/2026, 600 request ở trần 8000 token đầu vào/1000 token đầu ra có giá model tối đa minh họa 6,30 USD; nếu dùng xử lý theo vùng có phụ phí 10% thì 6,93 USD, **chưa xác minh thuế/phí của tài khoản**. Vì vậy chưa thể cam kết tổng 10 USD: cơ chế chặn trước cuộc gọi, điều kiện giá/phí và kiểm soát tài khoản phải được kiểm chứng trước. Cảnh báo trên dashboard không đủ. [Nguồn chính thức và giả định](GATE_A_SOURCES_61.md).

## Điều kiện còn thiếu

| Điều kiện | Ý nghĩa với Owner |
| --- | --- |
| Bộ dữ liệu giả lập đủ rộng và đáp án độc lập | Chưa thể đánh giá chất lượng 60 câu một cách trung thực |
| Bộ chặn chi phí, kiểm soát dữ liệu và thử lỗi offline | Hồ sơ mới là thiết kế, chưa chứng minh phần mềm thực thi được |
| Tài khoản/project, điều khoản, vùng xử lý, người giữ khóa, thuế/phí | Chưa kết nối; cần hồ sơ cụ thể trước khi xin phép dùng tài khoản/chi tiền |
| Đối chiếu taxonomy v1.0 | Chưa xác nhận đủ tên intent/giai đoạn/playbook/trạng thái; không đọc hay đưa tài liệu riêng lên repo |
| Kết quả AI và toàn hành trình | Tất cả NOT_RUN; 73 kiểm thử cũ chỉ là bằng chứng lõi giả lập |

Mẫu 100 lượt hiệu năng chỉ giúp quan sát ban đầu, không đủ chứng minh độ tin cậy production. Kết quả có thể phải ghi INCONCLUSIVE ngay cả khi không có lỗi quan sát được. Không tự tăng ngân sách để đạt kết luận đẹp hơn.

## Quyết định và bước tiếp theo

**Một bước tiếp theo được khuyến nghị:** Architecture Acceptance cho PR tài liệu này sau khi đọc [review độc lập](reviews/ISSUE_61_PREPARATION_REVIEW.md); chưa merge trước acceptance. Nghiệm thu giúp chốt phạm vi thử nghiệm và các điều kiện chặn; tác động hiện tại chỉ là tài liệu, có thể sửa/hoàn tác bằng PR tài liệu, không ảnh hưởng dịch vụ. Không cần Owner chọn schema, framework hay lệnh kiểm thử.

Sau đó, nếu Owner muốn tiếp tục, cần chỉ thị riêng cho việc tạo dữ liệu giả lập và triển khai/kiểm chứng kiểm soát offline. **Chỉ khi các điều kiện đã đủ**, Codex mới trình xin phép một lần chạy cụ thể: đúng model, tài khoản, trường dữ liệu, vùng/đích mạng, manifest SHA, thời gian, trần chi phí và cơ chế dừng. [Mẫu hồ sơ phê duyệt tương lai](GATE_A_MANIFEST_61.md) hiện còn UNKNOWN/PENDING_OWNER_APPROVAL; không phải giấy phép thực thi.

**Kết quả: GATE_A_PREPARATION_READY_FOR_OWNER.** Review Codex độc lập đã PASS tại SHA `99babe18fb1306f05d2f0ece1ed74ef0798eebcb`; một điểm về cách tính retry và một điểm diễn đạt đã được sửa, reviewer kiểm tra lại và không còn phát hiện cần xử lý. Đây là review độc lập bằng ngữ cảnh Codex mới, không phải formal GitHub approval hay chứng nhận thực thi. [Biên bản](reviews/ISSUE_61_PREPARATION_REVIEW.md) và [STATUS](STATUS.md) ghi bằng chứng. Không có thử nghiệm model/API, embeddings, tích hợp thật hay chi phí thử nghiệm trong nhiệm vụ chuẩn bị này.
