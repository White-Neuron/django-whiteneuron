---
name: Release Notes From Git Log
description: 'Generate professional release notes from git log for django-whiteneuron, including change summary, new features, risks, and upgrade notes.'
argument-hint: 'Version/tag range (optional), output language (vi|en), and audience (internal|public).'
agent: agent
---

Tạo release notes chuyên nghiệp từ git log trong workspace hiện tại.

Yêu cầu thực hiện:
1. Xác định phạm vi commit:
- Nếu người dùng cung cấp range/tag (ví dụ `v0.2.20..HEAD`) thì dùng phạm vi đó.
- Nếu không có, tự chọn phạm vi hợp lý: từ tag gần nhất đến `HEAD`.

2. Trích xuất và nhóm thay đổi từ git log:
- Nhóm theo chủ đề: `Features`, `Fixes`, `Improvements`, `Breaking Changes`, `Docs/Chore`.
- Loại bỏ commit noise không có giá trị phát hành (merge commit không mang nội dung, commit tạm).

3. Tạo release notes theo văn phong chuyên nghiệp:
- Có phần tóm tắt phát hành.
- Có mục thay đổi mới và tính năng mới.
- Nêu rõ rủi ro/ảnh hưởng tương thích nếu có.
- Có hướng dẫn nâng cấp ngắn gọn.
- Nếu đầu ra là tiếng Việt thì bắt buộc viết tiếng Việt có dấu.

4. Trả về kết quả gồm:
- `Release title`
- `Release notes` (Markdown)
- `Commit range used`
- `Key commits considered` (danh sách ngắn)

Mẫu cấu trúc mong muốn (Markdown):

## Tóm Tắt
...

## Thay Đổi Chính
- ...

## Tính Năng Mới
- ...

## Sửa Lỗi Và Cải Tiến
- ...

## Tương Thích Và Rủi Ro
- ...

## Hướng Dẫn Nâng Cấp
- ...
