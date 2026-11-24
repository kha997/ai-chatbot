# Issue #69 — Khắc phục bộ chấm offline sau kiểm toán Qoder

[Issue #69](https://github.com/kha997/ai-chatbot/issues/69) · [Biên nhận kiểm toán ban đầu đã lược bỏ thông tin riêng](https://github.com/kha997/ai-chatbot/issues/63#issuecomment-7112634718) · [Baseline 7e2a775](https://github.com/kha997/ai-chatbot/commit/7e2a775acfd542d5d4db0ac4c5b061e2214e37ae). Ngày 24/11/2026 (Asia/Saigon).

**Phạm vi đề nghị nghiệm thu:** cơ chế công khai được kiểm tra bằng mẫu giả, dùng để chuẩn bị cho người lưu giữ được ủy quyền. Phải có báo cáo Qoder đọc riêng mã công khai ở SHA kỹ thuật trước khi kết luận `OFFLINE_HARNESS_REMEDIATION_READY_FOR_OWNER`. Trong lúc chờ, trạng thái là **PARTIAL_REMEDIATION / BLOCKED — Qoder re-review pending**. Issue #63 giữ OPEN. Snapshot v2 có 60/60 ca được Owner duyệt nội dung theo biên nhận đã lược bỏ thông tin riêng. Kiểm chứng kỹ thuật độc lập bộ riêng, quyền truy cập và lưu giữ còn thiếu.

Quyết định [CHANGES_REQUIRED và báo cáo Qoder đã được tóm tắt](https://github.com/kha997/ai-chatbot/pull/70#issuecomment-7121276189) áp dụng SHA cũ. Qoder báo 27/30 ca đối kháng bị từ chối đúng, một lỗi thực tế, một giới hạn của ranh giới tin cậy và một hạn chế quan sát. Script ngoài repo vẫn chưa có để tái lập. Ma trận dưới đây là **kết quả triển khai vòng sửa**, chờ Qoder xác nhận SHA mới.

| Phát hiện | Kết quả triển khai bằng mẫu giả | Bằng chứng còn thiếu |
| --- | --- | --- |
| H1 — Hai định dạng byte | Giữ cầu nối `offline69-synthetic-bridge-v1 / PUBLIC_DUMMY` với pin SHA-256 và số byte cả hai đầu. Envelope khai báo cụ thể định dạng indented đầu vào và compact cho envelope/bộ chấm. | Mapping riêng và Snapshot v2 nằm ngoài phạm vi. |
| H2 — Lịch và envelope | Envelope đóng `offline69-mock-gate-a-v2` buộc designation, canonicalization và số ca. `small-dummy` phải có đúng 1–59 ca đã chốt; `full-dummy` buộc đúng 60 ID giả theo thứ tự. Cả số dòng, manifest và artifact nguồn phải khớp. | Lịch 60 ca giả chỉ xác minh cấu trúc. Bằng chứng Gate A riêng vẫn BLOCKED. |
| H3 — Trùng family/câu | Dùng chung NFKC, casefold và chữ/số cho family của toàn bộ corpus, bắt va chạm kiểu `a-b`/ `AB` và đối chiếu 12 ca phát triển đã ghim. | Độc lập về nghĩa, bản dịch và trùng ý cần reviewer riêng được phép xem bộ riêng. |
| H4 — Attestation | Giữ role separation, pins, seeds, zero-egress và evidence mock. External attestation chỉ nhận `NOT_VERIFIED`, kết quả thực chỉ nhận `NOT_RUN`. | Chữ ký Owner, ACL, lưu giữ và chứng cứ thực thi riêng vẫn BLOCKED. |
| H5 — Biên nhận | Giữ SQLite append-only, kiểm tra mốc mới nhất do bên ngoài giữ, và STOP qua mở lại. Kiểm thử cũ tiếp tục chạy. | Mốc bên ngoài đáng tin là điều kiện bắt buộc. Sổ giả không chứng minh WORM/chống rollback nếu cả mốc và máy bị thay. |
| H6 — Trace và CI | Guard chạy trên facts đã kiểm tra kiểu, trước kiểm tra liên kết để trả đúng `forbidden-typed-fact`. Kiểm thử phân biệt `schema`, `integer-fact` và `unsupported-output`. PR filter có `scripts/offline_corpus63.py` và `eval/offline63/**`. | Chấm văn bản tự do và trace riêng vẫn ngoài bằng chứng. Main CI trước đây là `NOT_RUN — no trigger`. |

## Hợp đồng byte và quyền

- `utf8-lf-sorted-keys-2spaces-v1` dùng UTF-8, sắp khóa, thụt hai dấu cách và một LF cuối. `utf8-lf-sorted-keys-compact-v1` dùng UTF-8, sắp khóa, dấu phân cách gọn và một LF cuối. Mảng giữ nguyên thứ tự. Cầu nối từ chối khóa trùng, số thực JSON, biểu diễn không canonical và Unicode không NFC. Bộ chấm offline67 vẫn nhận đúng định dạng compact như trước.
- Hàm [bridge](../scripts/offline_evidence69.py) nhận byte wrapper và descriptor đã được duyệt từ một ranh giới tin cậy, kiểm tra SHA-256 **và** số byte của đầu vào lẫn đầu ra. Nó dùng chính bundle có kiểu bên trong, không chuyển kiểu tự động, bỏ bớt trường lạ hoặc đổi phiên bản. Wrapper giữ provenance, revision, thời hạn, quyền và các trạng thái active/retired/revoked/untrusted. Entry nguồn không active không thể có quyền approved. Phần metadata bổ sung vẫn được giữ và khóa ở wrapper theo pin riêng.
- Bên kiểm tra mô phỏng dùng `verify` với pin envelope được cấp riêng trước khi đọc. Hàm xác minh các descriptor nguồn và dựng lại manifest đúng thứ tự, đối chiếu bộ dev cùng schema custody đã công bố, kiểm tra seed từng ca theo lịch chung. Một envelope v1 thiếu khai báo lịch/định dạng bị từ chối. Hash candidate/config là hash của **fixture**, không phải hash một bản build hoặc prompt có thật. Trạng thái trước và sau là trạng thái nghiệp vụ giả không đổi. Trace thu hồi nguồn có đường kiểm tra riêng trong offline67. Bản ghi attestation bên ngoài luôn `NOT_VERIFIED`; model, audit riêng, sáu E2E, hiệu năng và thanh toán luôn `NOT_RUN`. Mẫu không hỗ trợ quyền ghi, handoff hoặc thay đổi nghiệp vụ.
- `freeze_screened` tách kiểm tra cơ học khỏi phê duyệt. Chỉ dùng `development.json` công khai đúng revision, hash chuẩn hóa tính từ câu trong artifact này, cùng 12 họ tình huống thực. So khớp NFKC, casefold và chữ/số, với cùng quy tắc cho cả family nội bộ và họ ca phát triển. Các mã họ khác nhau vẫn có thể biểu đạt cùng một ý. `freeze` cũ của offline67 là hàm kỹ thuật cấp thấp, không chứng thực độc lập hoặc quyền.

## Sổ biên nhận mô phỏng

[Journal](../scripts/offline_journal69.py) lưu run, envelope/manifest pin, ca/nhóm/lượt/vị trí, dấu thời gian và thứ tự giả, digest input/observation, outcome, mã và hash nối trước đó. Vị trí phải đúng lịch. Nộp lại chỉ trả biên nhận cũ khi hai đầu vào và thời điểm khớp. STOP khóa lần ghi sau, kể cả qua mở lại. Gọi `evaluate` trực tiếp chỉ tạo kết quả chẩn đoán và không thể chèn biên nhận chính thức vào Journal. Sổ giữ digest, không giữ plaintext.

Mốc được duyệt ở nơi khác là đầu vào bắt buộc. Nếu commit SQLite xong mà người giữ mốc chưa cập nhật, mở lại với mốc cũ phải từ chối. Không lấy mốc từ SQLite để tự chữa. Giữ bằng chứng, đối chiếu với biên nhận bên ngoài và chỉ dùng lại sau quyết định đối soát độc lập. Sổ giả không có khóa ký thật hoặc WORM. Nếu cả SQLite lẫn mốc bên ngoài cùng bị tua ngược hoặc caller đặc quyền bị xâm phạm, cơ chế này không chứng minh chống rollback. Kết quả mô phỏng chỉ có hiệu lực trong phạm vi caller, dữ liệu và máy local đáng tin cậy.

PASS/FAIL là kết quả so với oracle của trace đủ. INCONCLUSIVE là trace chưa đủ, NOT_RUN là chưa có quan sát, STOP là từ chối quyền hoặc tính toàn vẹn. `required_reads` là phần bổ sung mô phỏng trên allowlist cũ. Một trace đầy đủ thiếu lần đọc bắt buộc sẽ STOP. ID có kiểu bị cấm cho kết quả STOP với mã `forbidden-typed-fact` khi trace hợp lệ đến điểm truy vết claim. Claim không hỗ trợ vẫn STOP với `unsupported-output`; trường tự do chưa khai báo bị từ chối với `schema`. Không có bằng chứng model, thực thi private hay giới hạn chi phí thực tế.

## Handoff cho Qoder, chỉ mã và mẫu giả công khai

Qoder đọc độc lập trong ngữ cảnh mới, không truy cập dữ liệu riêng, không sửa branch, không chạy model/provider chi phí và không merge. Tại **SHA kỹ thuật ghi trong PR**, đánh giá H1–H6 và các điểm trung bình theo `FIXED / PARTIAL / BLOCKED`. Ghi từng ca tái hiện, lệnh chạy, kết quả, thiếu sót và điểm dừng. Kiểm tra đặc biệt: thay hai định dạng pin, quyền nguồn đổi, câu dev chuẩn hóa, mốc ngoài bị cũ, crash sau commit, và ghi sau STOP. Đề nghị Qoder cung cấp **mã kiểm tra công khai an toàn hoặc mô tả tái hiện** cho 30 ca bên ngoài repo từ lần trước. Bộ PR này chưa tái chạy 30 ca đó.

Giữ các blocker `BLOCKED_PRIVATE_AUDIT`, `BLOCKED_HELDOUT_CUSTODY_WORKFLOW`, `BLOCKED_CORPUS_BREADTH` và `BLOCKED_COST_CONTROL`. AI, sáu E2E, Gate 2, Dispatcher, website/Zalo và production giữ NO-GO. PR chỉ để review, chờ Architecture Acceptance.

## Biên nhận kỹ thuật vòng đầu (lịch sử)

SHA kỹ thuật `0e3abff5d5698106b9e5a85ba4a4b9bffec379a3`. [Draft PR #70](https://github.com/kha997/ai-chatbot/pull/70) · [Yêu cầu tái kiểm toán Qoder](https://github.com/kha997/ai-chatbot/pull/70#issuecomment-7112970988).

- Windows `py -B -m unittest discover -s tests -p 'test_offline*.py'`: 74/74 PASS (15 ca mới, 59 hồi quy offline). `py -B -m unittest discover -s tests -p 'test_quote*.py'`: 73/73 PASS. Tổng 15 ca mới và đủ 132 ca hồi quy.
- Ubuntu-24.04 WSL với `unshare -Urn`: 74/74 offline và 73/73 quote PASS. Xác nhận chỉ có loopback đang down, không có tuyến IPv4/IPv6 trước khi chạy offline. Bật loopback trong namespace riêng chỉ cho bộ quote preview hiện có.
- `git diff --check 7e2a775acfd542d5d4db0ac4c5b061e2214e37ae HEAD`: PASS tại SHA kỹ thuật. Bốn CI tại SHA kỹ thuật PASS: [held-out và remediation](https://github.com/kha997/ai-chatbot/actions/runs/45258589984/job/137986885429), [corpus](https://github.com/kha997/ai-chatbot/actions/runs/45258589218/job/137986883302), [gateway](https://github.com/kha997/ai-chatbot/actions/runs/45258589706/job/137986886674), [quote](https://github.com/kha997/ai-chatbot/actions/runs/45258590635/job/137986888443). Commit báo cáo sau SHA này chỉ đổi tài liệu.
- Qoder mới: **PENDING**, đã đăng yêu cầu read-only tại SHA cố định. 30 ca bổ sung ngoài repo: **NOT_RUN / chưa có artifact tái lập**. Chưa có kết luận độc lập FIXED/PARTIAL/BLOCKED từ Qoder. Kiểm tra bộ riêng, provider/model và sáu E2E đều NOT_RUN; 0 chi phí thí nghiệm.

Worktree gốc sạch tại `b84f54ebac829b3d86762b642177c73212b01d05`. Issue #63 vẫn OPEN. Draft PR chưa merge.

## Biên nhận vòng sửa CHANGES_REQUIRED

SHA kỹ thuật [bd56785](https://github.com/kha997/ai-chatbot/commit/bd56785dadbf1ee7fb8343edfd89d9278862b12e). [Bàn giao Qoder chỉ đọc tại SHA mới](https://github.com/kha997/ai-chatbot/pull/70#issuecomment-7121343608). Báo cáo vòng mới **PENDING**.

- Windows: `py -B -m unittest discover -s tests -p 'test_offline*.py'` 78/78 PASS; `py -B -m unittest discover -s tests -p 'test_quote*.py'` 73/73 PASS. Tổng 132 hồi quy baseline, 15 ca remediation ban đầu và 4 ca bổ sung. Ca kiểm tra mệnh đề cấm còn đối chiếu đúng mã cho bốn đầu vào.
- WSL Ubuntu-24.04 `unshare -Urn`: cùng 78/78 và 73/73 PASS. Bộ offline chạy với loopback down và không tuyến IPv4/IPv6. Chỉ bật loopback trong namespace riêng để chạy hồi quy quote preview.
- Bốn job tại SHA kỹ thuật PASS: [harness/remediation](https://github.com/kha997/ai-chatbot/actions/runs/45321286585), [corpus](https://github.com/kha997/ai-chatbot/actions/runs/45321286547), [gateway](https://github.com/kha997/ai-chatbot/actions/runs/45321286781), [quote](https://github.com/kha997/ai-chatbot/actions/runs/45321286623). Kiểm thử filter xác minh hai đường dẫn nằm trong khối `pull_request.paths`; job harness tiếp tục dùng namespace cô lập và `contents: read`. `git diff --check` PASS.
- 30 ca ngoài repo của Qoder chưa được tái chạy trong vòng sửa. Issues #69 và #63 giữ OPEN. Không truy cập bộ riêng, chạy model, phát sinh chi phí hoặc merge.
