# Hồ sơ quyết định NHD MVP — Issue #59

Ngày kiểm tra: **23/11/2026**. Baseline đã nghiệm thu: [main 6243aa7](https://github.com/kha997/ai-chatbot/commit/6243aa7806b9209e3df810fbe34f1dab7bc51a40). Hồ sơ đang trình [PR #60](https://github.com/kha997/ai-chatbot/pull/60), **chờ Architecture Acceptance, chưa merge**. Đây là nghiên cứu kiến trúc; không phê duyệt chạy AI, chi tiền, dữ liệu thật hoặc triển khai.

## Khuyến nghị

**GO cho lập kế hoạch; CONDITIONAL GO cho một thử nghiệm AI giả lập có giới hạn sau phê duyệt riêng; NO-GO cho đưa hệ thống hiện tại vào sử dụng thật.**

Chọn Python với luồng xử lý đơn giản, dữ liệu sản phẩm/FAQ được duyệt, bộ tính báo giá xác định và một kết nối model có giới hạn chi phí. Model đề xuất thử đầu tiên là **GPT-5.4 mini bản `2026-03-17`**. Chưa cần LangGraph hoặc cả bộ RAGFlow/Mem0/Chatwoot. Giữ khả năng thay model và bổ sung LangGraph nếu luồng công việc thực tế phức tạp lên. Codex chịu trách nhiệm các lựa chọn kỹ thuật này; Owner không cần chọn thư viện.

## Chatbot NHD đầu tiên làm được gì?

Khách hỏi bằng tiếng Việt về sản phẩm hoặc nhóm sản phẩm; bot trả lời theo nguồn NHD đã duyệt, hỏi thêm quy cách/đơn vị/số lượng còn thiếu, và chỉ đưa **giá hoặc dự toán không ràng buộc** khi nguồn giá còn hiệu lực cho phép. Bot nêu rõ phần chưa bao gồm, không tự hứa tồn kho/giao hàng, không xác nhận đơn. Khi không đủ thông tin hoặc khách muốn gặp người, bot xin đồng ý chia sẻ nội dung tối thiểu và chuyển sang nhân viên phụ trách; chỉ báo “đã nhận” khi nhân viên xác nhận.

MVP không gồm thanh toán, tạo đơn, tích hợp ERP/CRM/Zalo/email, đọc tài liệu khách tải lên, tự học chính sách từ chat hoặc triển khai HANU/ZENA thật. Nếu NHD chưa duyệt giá để công bố, bot vẫn có thể tư vấn thông tin và thu thập yêu cầu, nhưng không báo giá.

## Hiện đã có gì, còn thiếu gì?

Lõi báo giá, handoff, quyền phiên giả lập và lưu ticket/đồng ý trong SQLite đã được nghiệm thu; PR #56 và #58 đều đã merge. **73/73 kiểm thử và preview 5/5 là kiểm thử giả lập**, không chứng minh AI hiểu tiếng Việt hoặc hệ thống an toàn để phục vụ khách thật.

Còn thiếu hội thoại LLM, kho thông tin NHD được duyệt, xác thực/khôi phục phiên thật, quản lý dữ liệu cá nhân, widget website và vận hành thật. Đặc biệt, SQLite hiện cho nhân viên giả lập xử lý tiếp sau restart nhưng chưa cho khách khôi phục quyền với ticket cũ. Đây là điều kiện phải giải quyết trước pilot dữ liệu thật, không phải việc có thể bỏ qua bằng một màn demo đẹp.

## Chi phí dự kiến

Các con số là dự toán minh họa, **không phải báo giá hay ngân sách đã duyệt**. Quy đổi giả định26.000 VND/USD, chưa thuế/phí tỷ giá. [Bảng tính, nguồn giá và độ nhạy](NHD_MVP_COST_ROADMAP_59.md) ghi đầy đủ lượt chat, token, hạ tầng và nhân công.

| Kịch bản/tháng | Tiền kỹ thuật (AI+hạ tầng) | Gồm công vận hành và nhân viên hỗ trợ |
| --- | ---: | ---: |
| 1.000 hội thoại | khoảng1,40 triệu VND | khoảng6,47 triệu VND |
| 10.000 hội thoại | khoảng9,35 triệu VND | khoảng41,59 triệu VND |
| 100.000 hội thoại | khoảng157,32 triệu VND | khoảng497,92 triệu VND |

Lưu lượng NHD hiện **chưa biết**. Tỷ lệ chuyển nhân viên, độ dài hội thoại và thông tin phải chuẩn hóa tác động lớn hơn việc chọn tên framework. Chi phí đầu tư kỹ thuật đến MVP nội bộ/pilot ước **20–33 ngày công**, tương đương **78–128,7 triệu VND có dự phòng25%** theo đơn giá giả định; chuẩn bị/duyệt nội dung kinh doanh và chi phí hợp đồng bảo mật/pháp lý chưa nằm trong đó. Đến production, tổng tích lũy ước **35–63 ngày công, 136,5–245,7 triệu VND** trên cùng giả định. Không cam kết thời hạn khi nguồn dữ liệu/nhân sự/phê duyệt chưa đủ.

Không chọn máy Ollama hiện có làm đường mặc định: tài nguyên và cô lập GPU chưa được chứng minh; “không mất tiền token” không đồng nghĩa vận hành miễn phí. Khi AI lỗi hoặc chạm ngân sách, dùng FAQ/form xác định hoặc nhân viên, không tự chuyển sang model trả phí khác.

## Điều kiện bắt đầu thử nghiệm và dùng thật

1. **Ngay bây giờ:** Owner/architecture advisor nghiệm thu hồ sơ PR #60 sau review độc lập. Chấp nhận hồ sơ không tự cấp quyền chạy model hay triển khai.
2. **Thử nghiệm AI giả lập riêng:** đề xuất tối đa600 request, model cố định trên, dữ liệu giả lập/công khai, trần10 USD tổng, không website/dữ liệu thật/thông báo; dừng ở giới hạn đầu tiên. Trước khi xin phép, Codex phải chốt manifest, tài khoản/quyền truy cập, điều khoản và cơ chế chặn chi phí có bằng chứng. Hiện chưa có quyền thực hiện.
3. **Pilot nội bộ riêng:** sau thử nghiệm đạt, cần nguồn mẫu NHD do người có thẩm quyền duyệt, người chịu trách nhiệm giá/nội dung/hỗ trợ, phạm vi dữ liệu và quyền xử lý rõ ràng, danh tính thật và phục hồi/xóa dữ liệu đã kiểm chứng. Đề xuất20 người thử nội bộ,200 hội thoại/hai tuần, trần kỹ thuật150 USD, chưa phục vụ khách công khai; mọi khoản và truy cập vẫn phải duyệt riêng.
4. **Sử dụng thật riêng:** chỉ sau kiểm thử độc lập bảo mật và đúng nguồn/giá/đồng ý đạt, backup/restore và kill switch đã diễn tập, có người trực và ngân sách, điều khoản/dữ liệu/site được duyệt. Triển khai canary nhỏ trước; mọi rò rỉ dữ liệu, giá bịa, tự duyệt chính sách hoặc vượt quyền đều là điều kiện dừng, dù điểm trả lời trung bình cao.

Ngưỡng đề xuất cho thử nghiệm: >=54/60 câu đúng mỗi lượt, nguồn hỗ trợ >=95% các luận điểm cần trích dẫn, **không sai giá/nguồn/quyền/đồng ý**, không tự nâng chat thành chính sách. Hiệu năng và chi phí phải đo; hiện mọi kết quả AI là NOT_RUN. [Tiêu chí chi tiết và trách nhiệm](NHD_MVP_COST_ROADMAP_59.md) là căn cứ nghiệm thu, không chỉ những tỷ lệ tóm tắt này.

## Quyết định cần Owner và dữ liệu còn thiếu

**Sáu ca nghiệm thu toàn hành trình đều chưa chạy.** (1) Cùng tên sản phẩm, trả đúng giá từng tenant. (2) Hỏi giá, dùng đúng nguồn được duyệt. (3) Lạm dụng hoặc ngoài phạm vi, phản hồi an toàn. (4) Quay lại chủ đề A sau B, giữ đúng thông tin của phiên. (5) Lỗi mạng/webhook, đối soát giao dịch và chống trùng. (6) Nhân viên tiếp quản thì bot dừng, chỉ tiếp tục khi được trả quyền hợp lệ. Ca 5–6 cần phê duyệt tích hợp riêng. Bản ma trận giữ nguyên các mục tiêu gốc và ghi rõ các điểm điều chỉnh, gồm Website Widget thay cho Facebook ở đợt đầu. Owner đối chiếu ma trận với tài liệu v1.0 riêng trước khi nghiệm thu kiến trúc. [Sáu ca và ma trận yêu cầu](NHD_PLATFORM_CONTRACTS_59.md#7-six-numbered-business-e2e-requirements--all-not_run)

**Quyết định hiện tại: Architecture Acceptance cho PR #60, nếu đồng ý với phương án mặc định và lộ trình.** Lợi ích là tập trung vào một hành trình NHD có thể kiểm chứng, tận dụng phần đã làm. Rủi ro là chất lượng AI và công chuẩn hóa dữ liệu vẫn chưa đo; hồ sơ giữ các điều kiện dừng rõ ràng. Tác động hiện tại chỉ là tài liệu; có thể sửa hoặc hoàn tác bằng PR tài liệu, không ảnh hưởng dịch vụ chạy.

Các phê duyệt ngân sách, tài khoản/provider, điều khoản/quyền dùng dữ liệu, hạ tầng và go-live sẽ được xin **riêng ở từng giai đoạn**, không gộp vào “accept” này. Owner chỉ cần cung cấp người duyệt nội dung kinh doanh và phạm vi kinh doanh mong muốn khi đến pilot; Codex tự xử lý thiết kế, schemas, tests và lựa chọn kỹ thuật.

Chưa có catalog/quy tắc giá NHD thật, lưu lượng, tỷ lệ chuyển đổi, quyền công bố dữ liệu hoặc lịch trực được xác minh. Không truy cập repository riêng để lấy chúng. Xem [kiểm kê và ADR](NHD_MVP_ARCHITECTURE_59.md), [nguồn chính thức](NHD_MVP_SOURCES_59.md), [review và validation](reviews/ISSUE_59_ARCHITECTURE_REVIEW.md).
