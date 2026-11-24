# Quy trình kiểm toán riêng Issue #63 — Giai đoạn A

Ngày 24/11/2026 (Asia/Saigon). Tài liệu này mô tả **quy trình do người lưu giữ được ủy quyền thực hiện** cho Snapshot v2 và bộ 60 ca riêng của [Issue #63](https://github.com/kha997/ai-chatbot/issues/63). Đây là quy trình chuẩn bị; **không phải phê duyệt truy cập dữ liệu riêng và không phải kết luận `HELDOUT_QUALIFIED`**. Không có nội dung, hash, URL, ID ca hay biên nhận riêng nào trong tài liệu này.

## 1. Mục tiêu và ranh giới

- Kiểm tra 60/60 ca riêng, 10 nhóm × 6 ca, hai lượt chấm, nguồn 37 claim, oracle, phép tính, từ chối/làm rõ, thu hồi nguồn, tính độc lập và custody.
- Chỉ dùng dữ liệu giả công khai để thử nghiệm quy trình. Dữ liệu riêng chỉ được xử lý sau khi Owner phê duyệt riêng biên giới dữ liệu và phương án truy cập.
- Không gửi dữ liệu riêng tới model cloud, dịch vụ AI, GitHub, CI, chat, email, webhook hay công cụ bên thứ ba.
- Không thay đổi Snapshot v2, không sửa oracle, không chấm lại để chọn kết quả tốt hơn, không merge và không mở Gate 2.

## 2. Vai trò và tách nhiệm

| Vai trò | Trách nhiệm | Không được làm |
| --- | --- | --- |
| Owner | Phê duyệt vị trí lưu trữ, ACL, thời hạn lưu/xóa, người lưu giữ, người review độc lập và biên nhận audit. | Không trực tiếp sửa oracle hoặc chấm thay reviewer. |
| Custodian | Giữ Snapshot v2, niêm phong manifest, chạy bộ chấm, giữ journal và external anchor, ghi access log. | Không tự duyệt nội dung, không tự sửa oracle, không kiêm reviewer ngữ nghĩa. |
| Corpus author | Tác giả 60 ca và 37 claim; ghi provenance/rights. | Không chấm ca do mình viết; không giữ quyền ghi oracle sau khi niêm phong. |
| Independent semantic reviewer (2 người) | Đọc từng ca, đối chiếu oracle–nguồn, đánh giá hành vi, trích dẫn, từ chối/làm rõ, độc lập với 12 ca phát triển. | Không là tác giả corpus, không là người viết runtime/prompt. |
| Security reviewer | Kiểm tra ACL, zero-egress, retention, tách vai trò, sự cố rò rỉ. | Không chấp nhận bằng chứng chỉ từ lời khai. |
| Runtime/prompt developer | Nhận đúng câu hỏi đã lên lịch và nguồn đã duyệt; không nhận oracle. | Không đọc Snapshot v2, oracle, nhãn chấm hoặc journal riêng. |
| Auditor (vai trò này) | Kiểm tra quy trình, môi trường, tính tái lập và báo cáo. | Không đọc oracle/ca riêng trong Giai đoạn A; không tự tuyên bố `HELDOUT_QUALIFIED`. |

Tách nhiệm bắt buộc: tác giả corpus, người viết runtime/prompt, người chấm ngữ nghĩa và người phê duyệt cuối là các cá nhân khác nhau. Một người không được giữ từ hai vai trò trở lên trong cùng một ca.

## 3. Điều kiện tiên quyết trước khi mở dữ liệu riêng

- [ ] Owner chỉ định **một** vị trí lưu trữ riêng do tổ chức kiểm soát, kèm ACL đọc/ghi, thời hạn lưu, thời hạn xóa và kênh phê duyệt.
- [ ] Custodian, hai reviewer ngữ nghĩa và security reviewer được chỉ định bằng tên; runtime/prompt developer nằm ngoài ACL.
- [ ] Vị trí riêng không nằm trong repo công khai, không nằm trong workspace đang được Qoder/IDE index, không đồng bộ OneDrive/Dropbox/Drive hay dịch vụ backup tự động.
- [ ] Có môi trường chạy offline đã kiểm chứng: không route, không DNS, không kết nối ra ngoài; Qoder/IDE/browser/model/API đã đóng.
- [ ] Có gói riêng đã niêm phong: byte/hash của 60 case, source bundle, oracle archive, custody schema, manifest, hai seed và thứ tự ID.
- [ ] Các lỗ hổng công cụ ở Mục 7 đã được sửa và có kiểm thử công khai; nếu chưa, dừng ở `BLOCKED`.
- [ ] Diễn tập công khai 60 ca dummy + 24 ca đối kháng + 12 hành trình đã PASS trên đúng bộ chấm sẽ dùng cho dữ liệu riêng.
- [ ] Owner phê duyệt riêng biên giới xử lý dữ liệu và phương án truy cập cho Giai đoạn B.

## 4. Môi trường chạy

### 4.1. Lựa chọn ưu tiên

Máy ảo hoặc máy riêng, hệ điều hành sạch, không cài Qoder/IDE/agent cloud, không có route mạng, không có dịch vụ đồng bộ, chỉ có Python chuẩn và bộ chấm đã pin. Dữ liệu riêng nằm trên volume mã hóa cục bộ, không mount vào workspace công khai.

### 4.2. Lựa chọn dự phòng đã kiểm chứng kỹ thuật

WSL Ubuntu-24.04 với network namespace riêng:

```sh
wsl.exe -l -v
timeout 60 wsl.exe -e sh -c "unshare -Urn sh -c 'ip -brief addr; echo NETNS_OK'"
timeout 60 wsl.exe -e sh -c "unshare -Urn sh -c 'python3 -B - <<\"PY\"
import socket
for host,port in ((\"1.1.1.1\",80),(\"8.8.8.8\",53)):
    try:
        socket.create_connection((host,port),2); print(host,\"CONNECTED\")
    except Exception as e: print(host,\"BLOCKED\",type(e).__name__)
try:
    socket.getaddrinfo(\"example.com\",443); print(\"DNS_RESOLVED\")
except Exception as e: print(\"DNS_BLOCKED\",type(e).__name__)
PY'"
```

Kỳ vọng: chỉ `lo` ở trạng thái `DOWN`; `NETNS_OK`; các kết nối và DNS đều `BLOCKED`. Nếu bất kỳ kết nối nào thành công, dừng và báo `BLOCKED`.

### 4.3. Điều cấm trong phiên xử lý dữ liệu riêng

- Không mở Qoder Desktop, IDE, trình duyệt, ứng dụng Office, trình xem ảnh/PDF hay bất kỳ ứng dụng có telemetry/cloud sync.
- Không copy/paste, không in, không chụp màn hình, không ghi clipboard, không gửi chat.
- Không chạy `git`, `gh`, CI, webhook, email, Zalo/SMS hay dịch vụ ngoài.
- Không gọi model/API, không dùng embeddings, không dùng dịch vụ chấm bằng AI.
- Không để file tạm, cache, log, SQLite, backup hoặc bản sao ngoài vị trí đã duyệt.

### 4.4. Giới hạn của máy Windows hiện tại

Phiên hiện tại **không có quyền admin**, nên không thể chứng minh chặn egress cấp Windows Firewall. Namespace WSL chỉ chứng minh tiến trình bên trong namespace không có route/DNS, không chứng minh toàn bộ host Windows. Vì vậy chỉ dùng WSL netns khi Owner/custodian xác nhận thêm: Qoder và mọi tiến trình index/telemetry đã đóng, dữ liệu riêng không nằm trong thư mục bị index, và không có ứng dụng đồng bộ chạy nền.

## 5. Phân loại kiểm tra

### 5.1. Kiểm tra tự động (máy làm, tái lập được)

| Mục | Cách kiểm tra | Kết quả mong đợi |
| --- | --- | --- |
| Toàn vẹn gói | SHA-256 và byte length của manifest, case, source bundle, oracle archive, custody schema; pin từ nguồn riêng. | Khớp 100%; sai một byte → STOP. |
| Cấu trúc corpus | 60 ID duy nhất, 10 nhóm × 6, đúng thứ tự, không trùng; 12 mã họ phát triển tách biệt. | 60/60; không trùng; không giao với dev. |
| Canonical bytes | UTF-8, khóa sắp xếp, một LF cuối, không float/khóa trùng/Unicode không NFC. | Chỉ nhận byte canonical. |
| Oracle số học | `totals` khớp Decimal chính xác giữa số lượng và đơn giá; không làm tròn ngầm. | Khớp tuyệt đối; sai → FAIL/STOP theo hợp đồng. |
| Hành vi và trích dẫn | `behavior`, `facts`, `links` khớp oracle; mọi claim bắt buộc có nguồn đã đọc, đúng tenant/version/paragraph/epoch. | PASS chỉ khi đủ; thiếu → INCONCLUSIVE/FAIL/STOP. |
| Nguồn bị thu hồi | Ca `ga61-qa-sources-06`: đọc trước thu hồi, thu hồi đúng tick, chặn giao sau thu hồi, không phát facts/citation/action. | Không có kết quả dựa trên nguồn đã thu hồi. |
| Claim bị cấm | `forbidden_fact_ids`, `forbidden_claims`, `forbidden_reads`, `forbidden_side_effects`. | Vi phạm → STOP, không chỉ FAIL. |
| Lịch và idempotency | 60 × 2, đúng thứ tự, không nhảy lượt, nộp lại cùng byte trả cùng biên nhận, STOP khóa ghi sau. | Không có kết quả thứ hai cho cùng vị trí. |
| Journal và external anchor | SQLite append-only; mở lại phải khớp anchor do bên ngoài giữ; anchor cũ → từ chối. | Không tự chữa anchor từ SQLite. |
| Rò rỉ công khai | Quét repo công khai không có 60 câu hỏi/đáp án, oracle, hash/URL riêng. | Không có dữ liệu riêng trong repo/PR/log. |

### 5.2. Kiểm toán ngữ nghĩa (người làm, không thể thay bằng máy)

- Câu hỏi có đúng ý định, không mơ hồ ngoài dự kiến; hành vi `answer/clarify/abstain/refuse` có đúng lý do.
- Câu trả lời đúng về nội dung, không chỉ đúng schema; trích dẫn thực sự hỗ trợ mệnh đề; không có claim phụ sai đi kèm.
- Ca từ chối/làm rõ hỏi đúng thông tin còn thiếu, không hỏi lại slot đã xác nhận, không từ chối câu trả lời được.
- Nguồn còn hiệu lực, đúng tenant/version/paragraph, không dùng nguồn retired/revoked/untrusted; đoạn trích khớp nguồn gốc.
- 60 ca độc lập về ý với 12 ca phát triển và với nhau; không chỉ khác chữ, không dịch/paraphrase, không đổi số lượng của cùng một bài toán.
- Không có chính sách/giá/tồn kho/consent nào do model tự tạo hoặc do chat tự nâng thành tri thức tổ chức.

Hai reviewer độc lập chấm từng ca; bất đồng không giải quyết được bằng bằng chứng → `INCONCLUSIVE`, không bỏ qua.

### 5.3. Kiểm toán custody (người + bằng chứng hệ thống)

- ACL thực tế: ai đọc, ai ghi, ai bị loại; access log có timestamp và danh tính.
- Retention/xóa: ngày bắt đầu, ngày xóa, biên nhận xóa, bản sao lưu.
- Zero-egress: log lệnh, ảnh chụp namespace, không có route/DNS/kết nối; không có model/API.
- Tách vai trò: danh tính tác giả, reviewer, custodian, runtime developer; không trùng vai trò.
- Biên nhận audit: manifest pin, lịch, kết quả, anchor, chữ ký/nhận của người có thẩm quyền.

## 6. Trình tự thực hiện

1. **Preflight:** xác nhận Owner approval, ACL, người tham gia, vị trí riêng, retention; chạy kiểm tra zero-egress; đóng Qoder/IDE/sync.
2. **Niêm phong:** custodian pin manifest, byte/hash 60 case, source bundle, oracle archive, custody schema, thứ tự ID và hai seed. Không chấm trước khi pin xong.
3. **Lượt 1:** chấm tuần tự 60 ca theo thứ tự đã pin; mỗi ca một bundle + observation; ghi journal; giữ nguyên STOP/FAIL/INCONCLUSIVE/NOT_RUN.
4. **Review ngữ nghĩa lượt 1:** hai reviewer độc lập đọc câu trả lời, trace và hard assertions; ghi bất đồng.
5. **Lượt 2:** lặp lại đúng lịch, seed và cấu hình; không chỉnh prompt/config giữa hai lượt; không chọn kết quả tốt hơn.
6. **Anchor:** cập nhật external anchor sau mỗi lần ghi; mở lại kiểm tra chain; lưu biên nhận.
7. **Kết luận:** chỉ báo `HELDOUT_QUALIFIED` khi 60/60 qua audit độc lập, nguồn/hash/ACL/retention/thu hồi đủ; nếu thiếu, giữ `BLOCKED_PRIVATE_AUDIT / BLOCKED_HELDOUT_CUSTODY_WORKFLOW`.

## 7. Lỗ hổng công cụ phải xử lý trước Giai đoạn B

Các điểm dưới đây được xác minh ở baseline `588b8fe1d3e54161fe194739d2c06552ca8c79f4`:

1. **`Run` không thực thi safeguard của bridge.** `Run.submit` gọi `evaluate` mà không truyền `required_reads`/`forbidden_fact_ids`; một trace thiếu lần đọc bắt buộc vẫn có thể PASS. `Journal` có kiểm tra này, nhưng `Journal` chỉ nhận envelope `PUBLIC_DUMMY`/manifest `dummy`. Cần sửa `Run` hoặc bắt buộc dùng một runner riêng đã kiểm thử.
2. **Không có journal bền vững cho chế độ `heldout`.** `verify()` và `Journal` bị khóa vào `PUBLIC_DUMMY`/`dummy`; chưa có đường chạy riêng đã kiểm thử cho 60 ca riêng. Cần bổ sung runner riêng + journal + external anchor và kiểm thử bằng dummy.
3. **`retrieval_relevance` chưa được chấm.** `custody.schema.json` khai báo trường này nhưng bộ chấm hiện tại không tính recall@5. Cần bổ sung nếu muốn chứng minh tiêu chí retrieval.
4. **Custody schema chưa đủ bằng chứng vận hành.** Schema chỉ là hợp đồng trường; không có access log, retention days, deletion receipt, zero-egress attestation, role-separation evidence. Cần mẫu biên nhận custody riêng.
5. **Chưa có validator nguồn riêng.** Validator công khai chỉ kiểm 37 claim công khai; `custody.schema.json` chỉ pin `source_bundle` bằng hash, không kiểm tenant/version/paragraph/excerpt/rights/revocation bên trong. Cần validator nguồn riêng hoặc quy trình kiểm tay có biên nhận.
6. **Chưa có ánh xạ custody case → scorer bundle.** Schema case riêng không chứa `totals`, `sources`, `revocations`; các trường writes/effects ở dạng phẳng khác bundle của bộ chấm; cần hợp đồng ánh xạ và kiểm thử trước khi chấm.

## 8. STOP và xử lý sự cố

Dừng ngay, giữ nguyên bằng chứng và báo Owner khi:

- Có bất kỳ kết nối mạng, DNS, model/API, upload, chat, email hoặc dịch vụ ngoài nào.
- Hash/byte không khớp pin; manifest/authority không xác minh được; thiếu nguồn bắt buộc.
- Truy cập ngoài ACL; vai trò trùng; reviewer mất độc lập; oracle bị sửa.
- Anchor ngoài bị cũ; journal không mở được; crash sau commit mà anchor chưa cập nhật.
- Phát hiện dữ liệu riêng trong repo, PR, log, clipboard, ảnh chụp hoặc thư mục tạm.

Không retry để che lỗi; không chấm lại để thay kết quả; không dùng SQLite để tự chữa anchor. Nếu công việc cần gửi nội dung riêng tới dịch vụ AI, **dừng và yêu cầu Owner quyết định**.

## 9. Lưu giữ, xóa và sự cố rò rỉ

- Owner quy định thời hạn lưu nội dung riêng và audit; custodian ghi ngày bắt đầu/kết thúc/xóa.
- Journal, receipt, access log và anchor lưu trong vị trí riêng; không đưa hash/URL/ID nhạy cảm lên GitHub.
- Khi hết hạn: xóa theo chính sách, ghi biên nhận xóa, xác nhận không còn bản sao backup/cache.
- Khi rò rỉ: thu hồi quyền, đánh dấu release bị nhiễm, tiêu hủy bản sao theo chính sách, thông báo Owner và làm lại release mới.

## 10. Mẫu biên nhận tối thiểu (riêng)

| Trường | Nội dung |
| --- | --- |
| Run/manifest pin | ID lần chạy, SHA-256 manifest, phiên bản schema, commit công khai của bộ chấm. |
| Case/repetition | ID ca, nhóm, lượt, vị trí lịch; không có câu hỏi/đáp án trong biên nhận công khai. |
| Input/observation digest | SHA-256 byte đã nộp; không lưu plaintext trong receipt. |
| Outcome/code | PASS/FAIL/INCONCLUSIVE/STOP/NOT_RUN và mã cố định. |
| Authority | Nguồn/version/paragraph/epoch, sự kiện thu hồi, lần giao bị chặn. |
| Custody | Người chấm, reviewer, custodian, ACL, access log, retention/xóa, zero-egress. |
| Anchor | Hash nối trước, anchor bên ngoài, thời điểm cập nhật. |

## 11. Kết luận Giai đoạn A

Quy trình này **sẵn sàng để Owner xem xét phê duyệt**, nhưng môi trường và công cụ chưa đủ để mở dữ liệu riêng. Trạng thái tương ứng là `PRIVATE_AUDIT_ENVIRONMENT_BLOCKED` cho đến khi các điều kiện ở Mục 3 và lỗ hổng ở Mục 7 được đóng bằng bằng chứng tái lập.
