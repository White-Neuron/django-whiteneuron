# Báo Cáo Nâng Cấp django-unfold

## 1. Tổng Quan
- Ngày thực hiện:
- Phạm vi nâng cấp:
- Mục tiêu yêu cầu:
- Kết quả: thành công | một phần | bị chặn
- Mức độ rủi ro tổng thể: thấp | trung bình | cao

## 2. Thay Đổi Version Và Dependency
- Version trước:
- Version mới:
- Thay đổi trong `pyproject.toml`:
- Thay đổi trong `uv.lock`:
- Lệnh đã chạy:

```bash
# Example
uv add "django-unfold>=<target_version>"
uv sync
uv run python whiteneuron/manage.py check
```

## 3. Đánh Giá Tác Động Từ Changelog
- Release notes đã đối chiếu:
- Các thay đổi có khả năng gây vỡ liên quan đến dự án:
- API/tính năng deprecate ảnh hưởng đến code custom:

## 4. Thay Đổi Mới Và Tính Năng Mới Của Bản Vừa Cài
- Danh sách thay đổi mới (tóm tắt):
  - Mục 1:
    - Mô tả ngắn:
    - Mức độ tác động: no impact | optional adoption | required code change
    - Thành phần bị ảnh hưởng trong dự án:
  - Mục 2:
    - Mô tả ngắn:
    - Mức độ tác động: no impact | optional adoption | required code change
    - Thành phần bị ảnh hưởng trong dự án:
- Danh sách tính năng mới:
  - Tính năng 1:
    - Mô tả:
    - Đề xuất: adopt now | defer
    - Lý do:
    - Việc cần làm nếu adopt:
  - Tính năng 2:
    - Mô tả:
    - Đề xuất: adopt now | defer
    - Lý do:
    - Việc cần làm nếu adopt:
- Các thay đổi không áp dụng cho dự án (nếu có):

## 5. Đánh Giá Tương Thích Theo Hotspot
- Settings (`UNFOLD`, contrib apps): pass | warning | fail
- Tích hợp Python admin: pass | warning | fail
- Template override: pass | warning | fail
- Templatetag override: pass | warning | fail
- Widgets/forms/decorators: pass | warning | fail

## 6. Vấn Đề Phát Hiện Và Cách Xử Lý
- Vấn đề 1:
  - Triệu chứng:
  - Nguyên nhân gốc:
  - Cách sửa đã áp dụng:
  - Bằng chứng kiểm chứng:
- Vấn đề 2:
  - Triệu chứng:
  - Nguyên nhân gốc:
  - Cách sửa đã áp dụng:
  - Bằng chứng kiểm chứng:

## 7. Kết Quả Kiểm Chứng
- Kiểm tra kỹ thuật:
  - `manage.py check`:
  - Test đã chạy:
  - Kiểm tra bổ sung:
- Kiểm tra smoke thủ công:
  - Trang login:
  - Trang index/dashboard admin:
  - Change list:
  - Change form:
  - Filters/pagination/actions:

## 8. Rủi Ro Còn Lại Và Khoảng Trống
- Rủi ro còn lại:
- Khu vực chưa được test:
- Khuyến nghị theo dõi:

## 9. Kế Hoạch Rollback
- Điều kiện kích hoạt rollback:
- Lệnh rollback:

```bash
# Ví dụ rollback
# 1) Khôi phục commit lockfile trước đó
# 2) uv sync
# 3) Chạy lại smoke checks
```

## 10. Hành Động Tiếp Theo
- [ ] Việc 1
- [ ] Việc 2
- Người phụ trách:
- Hạn hoàn thành:
