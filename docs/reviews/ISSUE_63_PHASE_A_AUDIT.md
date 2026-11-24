# Issue #63 — Báo cáo kiểm toán độc lập Giai đoạn A

Ngày 24/11/2026 (Asia/Saigon). Vai trò: **Independent Technical Auditor**. Baseline kiểm toán: [`588b8fe1d3e54161fe194739d2c06552ca8c79f4`](https://github.com/kha997/ai-chatbot/commit/588b8fe1d3e54161fe194739d2c06552ca8c79f4) (`origin/main`, merge PR #70). Phạm vi: **chỉ Giai đoạn A** — xác minh môi trường, đọc hợp đồng/công cụ offline đã merge và chuẩn bị quy trình cho người lưu giữ. **Không truy cập Snapshot v2, không mở 60 câu hỏi/đáp án, không đọc oracle, không chạy model/API và không phát sinh chi phí.**

Tài liệu liên quan: [Quy trình kiểm toán riêng](../PRIVATE_AUDIT_PROCEDURE_63.md) · [Hợp đồng #67](../OFFLINE_HELDOUT_67.md) · [Khắc phục #69](../OFFLINE_REMEDIATION_69.md) · [Manifest Gate A](../GATE_A_MANIFEST_61.md) · [Custody schema](../../eval/offline63/custody.schema.json).

## 1. Kết luận điều hành

**`PRIVATE_AUDIT_ENVIRONMENT_BLOCKED`.**

Quy trình kiểm toán đã được viết và có thể trình Owner phê duyệt, nhưng **môi trường và công cụ chưa đủ để mở dữ liệu riêng**:

- Không có vị trí lưu trữ riêng, ACL, người lưu giữ hoặc reviewer độc lập nào được chỉ định.
- Qoder Desktop — môi trường đang chạy phiên này — là **cloud-backed**, có index workspace, telemetry và buffer hội thoại cục bộ; không phải môi trường zero-egress cho dữ liệu riêng.
- WSL `unshare -Urn` chứng minh được zero-egress ở mức tiến trình, nhưng host Windows hiện không có quyền admin và chưa chứng minh chặn egress toàn host.
- Bộ chấm/durable journal hiện có **không có đường chạy `heldout` đã kiểm thử**: `Run` không thực thi `required_reads`/`forbidden_fact_ids`; `Journal` bị khóa vào `PUBLIC_DUMMY`/`dummy`.
- `retrieval_relevance`, bằng chứng custody vận hành và validator nguồn riêng chưa được triển khai.

Issue #63 giữ **OPEN**; bốn blocker hiện tại vẫn mở: `BLOCKED_PRIVATE_AUDIT`, `BLOCKED_HELDOUT_CUSTODY_WORKFLOW`, `BLOCKED_CORPUS_BREADTH`, `BLOCKED_COST_CONTROL`. Không merge, không deploy, không mở Gate 2.

## 2. Bảng PASS / FAIL / BLOCKED

| Mục | Kết quả | Bằng chứng / lý do |
| --- | --- | --- |
| A1. Đọc hợp đồng #67, #69, manifest #61, custody schema, bộ chấm/bridge/journal | **PASS** | Đã đọc tại baseline; không thấy mâu thuẫn chặn việc chuẩn bị. |
| A2. Xác minh baseline và lịch sử merge | **PASS** | `git fetch origin` cập nhật `origin/main` từ `7e2a775` lên `588b8fe`; `origin/main` là merge PR #70; worktree audit tạo đúng `588b8fe`. |
| A3. Toàn vẹn 5 artifact công khai | **PASS** | 5/5 file khớp `byte_length` và `sha256` trong `eval/offline63/manifest.json` (coverage, custody schema, development, public schema, sources). |
| A4. Cấu trúc corpus công khai | **PASS** | 60 slot đã đặt trước, 10 nhóm × 6, tất cả `state: reserved`; 37 claim; 12 ca phát triển/12 family; `Held-out frozen: 0`. |
| A5. Hồi quy tự động offline | **PASS** | `py -B -m unittest discover -s tests -p 'test_offline*.py'` → **78/78 PASS**; `test_quote*.py` → **73/73 PASS**. |
| A6. Validator corpus công khai | **PASS** | `py -B -m scripts.offline_corpus63` → `Validated 9 products, 37 source claims, 12 public development oracles and 60 reserved slots. Held-out frozen: 0.` |
| A7. Không có dữ liệu riêng trong repo công khai | **PASS** | Quét chỉ thấy 60 ID `ga61-qa-*` trong inventory/schema/docs công khai; không có cặp câu hỏi–đáp án riêng, oracle archive, hash/URL riêng; không có file >200 KB. |
| A8. Zero-egress ở mức namespace WSL | **PASS (một phần)** | `unshare -Urn` → chỉ `lo` DOWN, `NETNS_OK`; kết nối `1.1.1.1:80`/`8.8.8.8:53` `BLOCKED OSError`; DNS `BLOCKED gaierror`. |
| A9. Qoder Desktop dùng được cho dữ liệu riêng | **FAIL** | Log `qoder-context` có 468 tham chiếu `https://openapi.qoder.sh` và 1.753 sự kiện indexing; có `startup-telemetry.json`, hàng đợi RUM, buffer hội thoại SQLite cục bộ. |
| A10. Vị trí lưu trữ riêng, ACL, custodian, reviewer | **BLOCKED** | Chưa có chỉ định của Owner; `custody.schema.json` chỉ là hợp đồng trường, không có access log/retention/deletion/zero-egress evidence. |
| A11. Durable journal cho chế độ `heldout` | **BLOCKED** | `verify()` yêu cầu `scope == PUBLIC_DUMMY` và `manifest.mode == dummy`; `Journal` chỉ nhận `ApprovedRun` từ `verify()`. Không có đường riêng đã kiểm thử. |
| A12. `Run` thực thi `required_reads`/`forbidden_fact_ids` | **FAIL** | Tái hiện: `Run` trả `PASS matched` với trace **không đọc nguồn nào**, dù oracle `reads` có nguồn. `Run.submit` không có tham số `required_reads`; `evaluate` được gọi không truyền `forbidden_fact_ids`. `Journal` có kiểm tra nhưng không dùng được cho `heldout`. |
| A13. Chấm `retrieval_relevance` / recall@5 | **BLOCKED** | Trường có trong `custody.schema.json` nhưng không được bộ chấm hiện tại sử dụng; không có hàm tính recall@5. |
| A14. Validator nguồn riêng (37 claim, excerpt, rights, revocation) | **BLOCKED** | Validator công khai chỉ kiểm nguồn công khai; schema riêng chỉ pin `source_bundle` bằng hash, không kiểm cấu trúc bên trong. |
| A15. Ánh xạ custody case → scorer bundle | **BLOCKED** | Case schema riêng không chứa `totals`, `sources`, `revocations`, `writes/effects`; chưa có hợp đồng ánh xạ/kiểm thử. |
| A16. Kiểm toán 60 ca riêng và oracle–nguồn | **NOT_RUN** | Chưa được phép truy cập Snapshot v2/bộ 60 ca; đây là Giai đoạn B. |
| A17. Độc lập ngữ nghĩa với 12 ca phát triển | **NOT_RUN** | Kiểm tra cơ học NFKC/casefold có, nhưng đánh giá trùng ý/dịch/paraphrase cần reviewer người được ủy quyền xem dữ liệu riêng. |
| A18. Chi phí thử nghiệm | **PASS** | 0 model/API call; 0 VND; chỉ chạy Python/stdlib và WSL cục bộ. |

## 3. Bằng chứng môi trường

### 3.1. Qoder Desktop không phải môi trường zero-egress

Đã kiểm tra thư mục cấu hình/dữ liệu người dùng Qoder (không đọc nội dung hội thoại riêng):

- `qoder-context.log`: **468** tham chiếu `https://openapi.qoder.sh`; **1.753** sự kiện `indexing`; daemon `qoder-search` index workspace.
- `chat-session-turn-payload-buffer.sqlite`: bảng `pending_turn_projections` (0 dòng) và `active_turn_projection_items` (**132 dòng**); đây là buffer cục bộ của các lượt hội thoại.
- `logs/*/startup-telemetry.json`, `rum-electron-store/offline-queue/` và `qoder-data.v1.json` (có `turns`, `turnInputs`, `sessionDeliveries`) cho thấy telemetry/lưu trữ cục bộ.
- Không tìm thấy cấu hình opt-out telemetry/indexing trong các tệp đã kiểm tra; `settings.json` chỉ chứa plugin.
- Phát hiện thêm: `mcp-router.json` chứa credential cục bộ dạng plaintext (giá trị **không** được sao chép vào báo cáo). Đây là rủi ro cấu hình cục bộ, không phải dữ liệu kiểm toán.

**Kết luận:** không mở Snapshot v2, câu hỏi, đáp án, nguồn hay biên nhận riêng trong Qoder/chat/agent cloud. Mọi thao tác với dữ liệu riêng phải do custodian thực hiện trong môi trường đã duyệt.

### 3.2. Zero-egress kỹ thuật đã kiểm chứng

Máy hiện tại: Windows, **không có quyền admin** (`net session` → `NOT_ADMIN`). WSL có `Ubuntu-24.04` đang chạy. Trong network namespace riêng:

- `ip -brief addr` chỉ còn `lo DOWN`.
- `socket.create_connection(("1.1.1.1",80))` và `("8.8.8.8",53)` đều `BLOCKED OSError`.
- `socket.getaddrinfo("example.com",443)` → `DNS_BLOCKED gaierror`.

Đây là bằng chứng tốt cho **tiến trình bên trong namespace**, không phải cho toàn host Windows. Vì không có admin, chưa thể chứng minh Windows Firewall hoặc chặn egress cấp host. Quy trình yêu cầu custodian xác nhận thêm Qoder/IDE/sync đã đóng và dữ liệu riêng nằm ngoài workspace bị index.

## 4. Bằng chứng công cụ và dữ liệu công khai

- 5/5 artifact khớp hash/byte trong manifest.
- `coverage.json`: 60 slot, 10 category, tất cả `reserved`; không có câu hỏi/đáp án.
- `sources.json`: 37 claim, tất cả tenant NHD; 34 `active`, 1 `retired`, 1 `revoked`, 1 `untrusted`; 33 `permitted`, 4 không; 8 family; 26 document.
- Phát hiện có chủ đích trong nguồn công khai: một cặp `available-count` 3 vs 5 cùng subject/predicate (kịch bản xung đột availability) và một claim giá `active` nhưng `permitted: false` (kịch bản từ chối công bố giá). Không phải lỗi dữ liệu; reviewer ngữ nghĩa phải xác nhận chúng được gắn đúng ca.
- `development.json`: 12 ca, 12 family, `split: public-development`, `scoring: false`.
- `py -B -m scripts.offline_corpus63`: 9 product, 37 claim, 12 dev oracle, 60 reserved, **held-out frozen: 0**.
- Test: 78/78 offline, 73/73 quote PASS trên Windows.

## 5. Phát hiện và mức độ

| ID | Mức | Phát hiện | Bằng chứng | Tác động |
| --- | --- | --- | --- | --- |
| F1 | HIGH | Qoder là cloud agent, index workspace, telemetry và buffer hội thoại cục bộ. | Mục 3.1 | Không thể dùng Qoder cho dữ liệu riêng; nguy cơ rò rỉ sang `openapi.qoder.sh`. |
| F2 | HIGH | Chưa có vị trí riêng/ACL/custodian/reviewer được Owner chỉ định. | `docs/OFFLINE_CORPUS_63.md` mục “Held-out custody decision”. | Không thể bắt đầu Giai đoạn B; không có bằng chứng quyền truy cập/lưu giữ. |
| F3 | HIGH | Durable journal không hỗ trợ `heldout`/private. | `scripts/offline_evidence69.py` yêu cầu `PUBLIC_DUMMY` và `manifest.mode == dummy`; `scripts/offline_journal69.py` nhận `ApprovedRun`. | Không có lịch 60×2 bền vững, chống rollback, đã kiểm thử cho dữ liệu riêng. |
| F4 | HIGH | `Run` không thực thi safeguard `required_reads`/`forbidden_fact_ids`. | `scripts/offline_heldout67.py` `Run.submit` gọi `evaluate` không truyền hai tham số; demo trả `PASS matched` với `reads=[]`. | Trace thiếu lần đọc bắt buộc vẫn có thể PASS nếu dùng `Run` như tài liệu #67 chỉ định. |
| F5 | MEDIUM | `retrieval_relevance` không được chấm. | Có trong `custody.schema.json`; không có reference trong `scripts/offline_heldout67.py`. | Không chứng minh được recall@5/tiêu chí retrieval. |
| F6 | MEDIUM | Custody schema thiếu bằng chứng vận hành. | Không có access log, retention days, deletion receipt, zero-egress attestation, role-separation evidence. | Không đủ để chứng minh custody/ACL/retention trước `HELDOUT_QUALIFIED`. |
| F7 | MEDIUM | Chưa có validator nguồn riêng và ánh xạ case → bundle. | Validator công khai chỉ kiểm nguồn công khai; schema riêng không có `totals`/`sources`/`revocations`/excerpt. | Không thể tự động kiểm 37 claim/excerpt/arithmetic cho bộ riêng. |
| F8 | LOW | Credential MCP cục bộ dạng plaintext. | `mcp-router.json` (giá trị không sao chép). | Rủi ro cục bộ; nên chuyển sang secret store/rotate; không liên quan dữ liệu kiểm toán. |
| F9 | INFO | Zero-egress WSL hoạt động; host residual chưa chứng minh. | `NETNS_OK`, DNS/connect BLOCKED, `NOT_ADMIN`. | Cần xác nhận host/VM và đóng Qoder/sync trước Giai đoạn B. |

## 6. Sai lệch giữa oracle và nguồn

- **Công khai:** không có oracle theo từng ca private trong repo; 12 dev oracle được validator/test công khai kiểm tra và PASS. Không phát hiện sai lệch số học/cấu trúc trong phạm vi công khai. Hai đặc điểm nguồn có chủ đích (xung đột availability 3 vs 5; giá active nhưng không permitted) cần reviewer ngữ nghĩa xác nhận gắn đúng ca, không phải lỗi tự động.
- **Riêng:** **NOT_RUN**. Không có quyền truy cập Snapshot v2/bộ 60 ca, nên không thể kết luận oracle–nguồn, phép tính, từ chối/làm rõ hay độc lập ngữ nghĩa. Đây là `NOT_RUN`, không phải `PASS`.

## 7. Ca cần sửa

- **Ca riêng:** chưa kiểm tra nên **không thể** liệt kê ca cần sửa. Không được suy đoán từ inventory công khai.
- **Công khai:** không có ca nào fail; 78/78 offline và 73/73 quote PASS.
- **Công cụ/hợp đồng cần sửa trước Giai đoạn B:** F3 (journal private), F4 (`Run` safeguard), F5 (retrieval), F6 (custody evidence), F7 (source validator + mapping). Chi tiết ở [quy trình](../PRIVATE_AUDIT_PROCEDURE_63.md#7-lỗ-hổng-công-cụ-phải-xử-lý-trước-giai-đoạn-b).

## 8. Rủi ro bảo mật và mất tính độc lập

- **Rò rỉ qua agent cloud:** Qoder gửi prompt/context tới `openapi.qoder.sh`; index workspace và lưu buffer hội thoại. Bất kỳ dữ liệu riêng nào mở trong phiên này đều có thể rời máy. Biện pháp: không dùng Qoder/IDE/agent cloud cho dữ liệu riêng; chỉ dùng môi trường offline đã duyệt.
- **Index/telemetry/log cục bộ:** daemon index, startup telemetry, RUM queue và buffer SQLite có thể lưu nội dung ngoài ý muốn. Biện pháp: dữ liệu riêng ngoài workspace index; đóng ứng dụng; xóa cache/log theo chính sách; kiểm tra lại trước khi mở dữ liệu.
- **Host-level egress:** không có admin, chưa chứng minh chặn toàn host. Biện pháp: VM/máy riêng hoặc xác nhận firewall/network của Owner; WSL netns chỉ là lớp thứ hai.
- **Mất độc lập:** chưa có custodian/reviewer được chỉ định; tác giả corpus, người viết runtime và reviewer phải khác nhau. Auditor (Qoder) **không** thấy oracle, nhưng Qoder cũng là công cụ của phía phát triển; review ngữ nghĩa cuối phải do người/phiên độc lập được ủy quyền, không dùng AI judge API.
- **Repo công khai:** có nguy cơ commit nhầm private data/hash/URL. Biện pháp: `.gitignore` đã chặn DB/transcript/private-data; vẫn phải quét trước mỗi PR và không đưa biên nhận riêng lên GitHub.
- **Nhiễm pretraining:** không thể chứng minh model chưa từng thấy dữ liệu công khai tương tự; báo cáo phải giữ giới hạn này.

## 9. Bằng chứng còn phải do người kiểm toán được ủy quyền cung cấp

- Quyết định của Owner về vị trí lưu trữ riêng, ACL đọc/ghi, retention/xóa, người lưu giữ và reviewer độc lập.
- Danh tính/tách nhiệm của author, custodian, hai reviewer ngữ nghĩa, security reviewer và runtime developer.
- Pin manifest, byte/hash 60 case, source bundle, oracle archive, hai seed và thứ tự ID.
- Access log, biên nhận retention/xóa, bằng chứng zero-egress trên đúng host/VM sẽ dùng.
- Kết quả 60/60 ca, 37 claim, source revocation `ga61-qa-sources-06`, hai lượt chấm và anchor bên ngoài.
- Biên nhận audit độc lập có chữ ký/nhận của người có thẩm quyền; không đưa hash/URL/ID nhạy cảm lên GitHub.

## 10. Điều kiện còn thiếu trước `HELDOUT_QUALIFIED`

1. Owner phê duyệt riêng biên giới dữ liệu và phương án truy cập Giai đoạn B.
2. Đóng F2–F7 bằng mã/hợp đồng đã kiểm thử công khai; đặc biệt là runner private có `required_reads`/`forbidden_fact_ids`, journal bền vững + external anchor, retrieval recall, validator nguồn và ánh xạ custody case → bundle.
3. Diễn tập công khai đầy đủ 60 dummy × 2 + 24 đối kháng + 12 hành trình trên đúng bộ chấm sẽ dùng cho dữ liệu riêng.
4. Kiểm toán 60/60 ca riêng: cấu trúc, oracle, 37 claim, hiệu lực/quyền, thu hồi nguồn, độc lập ngữ nghĩa, hai lượt, journal/anchor, custody.
5. Hai reviewer ngữ nghĩa độc lập PASS; bất đồng còn lại → `INCONCLUSIVE`, không được offset bằng điểm trung bình.
6. Bằng chứng ACL/retention/xóa/zero-egress và biên nhận audit riêng; không có dữ liệu riêng trên GitHub/CI/chat.

## 11. Trạng thái kết thúc Giai đoạn A

**`PRIVATE_AUDIT_ENVIRONMENT_BLOCKED`.**

Quy trình đã sẵn sàng để Owner xem xét, nhưng môi trường và công cụ chưa đạt điều kiện mở dữ liệu riêng. Không tuyên bố `HELDOUT_QUALIFIED`; không merge; không deploy; không mở Gate 2; không phát sinh chi phí. Issue #63 giữ **OPEN** cùng bốn blocker hiện tại.
