# Giới thiệu django-whiteneuron

django-whiteneuron là một extension Django Admin hiện đại, được xây dựng trên nền tảng [django-unfold](https://github.com/unfoldadmin/django-unfold), cung cấp bộ công cụ toàn diện cho việc quản trị website: dashboard trực quan, hệ thống thông báo real-time, quản lý file, thu thập feedback, rate limiting, blacklist IP/User-Agent, và nhiều tính năng nâng cao khác.

## Tại sao django-whiteneuron?

### Vấn đề với Django Admin mặc định

Django Admin là một công cụ mạnh — nhưng khi dự án phát triển, bạn thường cần:

- **Dashboard tùy chỉnh** với KPI, biểu đồ, số liệu thực tế
- **Thông báo real-time** khi có thay đổi dữ liệu quan trọng
- **Theo dõi hoạt động** của user và khách truy cập
- **Rate limiting** bảo vệ admin khỏi spam/brute-force
- **Blacklist IP/User-Agent** chặn bot, crawler độc hại
- **Quản lý file** với xác minh tính toàn vẹn (SHA-256)
- **Thu thập feedback** trực tiếp trên từng model trong admin

django-whiteneuron giải quyết tất cả những nhu cầu này trong một package duy nhất.

## Tính năng nổi bật

### 1. Dashboard quản trị trực quan

Dashboard tích hợp sẵn KPI cards và biểu đồ hoạt động 28 ngày, phân tách theo user đã đăng nhập / khách truy cập, thành công / lỗi. Hỗ trợ lọc theo thời gian: hôm nay, 7 ngày, tuần, tháng, năm — với so sánh period-over-period.

### 2. Thông báo real-time qua WebSocket

Mọi thao tác CRUD trên model kế thừa `BaseModel` đều tự động tạo thông báo gửi đến toàn bộ superuser qua WebSocket + JavaScript alert. Hiển thị chi tiết trường nào thay đổi, ai thực hiện, link đến object trong admin.

### 3. Theo dõi hoạt động đầy đủ

- **UserActivity**: Log mọi request của user đã đăng nhập
- **AnonymousActivity**: Log request của khách truy cập
- **VisitProfile**: Gom nhóm theo IP + User-Agent

Dữ liệu bao gồm: path, method, body data (sanitize sensitive fields), status code, timestamp, thời gian thực thi.

### 4. Rate limiting hai lớp

| Lớp | Phạm vi | Cơ chế |
|---|---|---|
| IP-based | Theo địa chỉ IP | Redis-backed, hỗ trợ CIDR |
| User-based | Theo user đăng nhập | Redis-backed, per-user counter |

Khi vượt giới hạn: API trả JSON 429, browser hiển thị trang 429 với `Retry-After`.

### 5. Blacklist IP/User-Agent kép

**Static** — cấu hình trong `.env`, hỗ trợ CIDR (IPv4/IPv6), load khi khởi động.

**Dynamic** — quản lý qua admin panel, có thể block tạm thời với TTL tự hết hạn qua Redis, không cần restart server.

### 6. Quản lý file với xác minh tính toàn vẹn

Mọi file upload đều được tính hash SHA-256 tự động. Có thể kiểm tra tính toàn vẹn bất kỳ lúc nào bằng `.verify_integrity()`. Hỗ trợ Excel và PDF.

### 7. Custom User Model

- UUID unique identifier
- Avatar, biography
- Bot account support (`is_bot` flag)
- Auto-generate password + gửi email đăng nhập khi tạo user mới từ admin
- Grid view card-based với avatar, status badges, role indicators

### 8. Soft Delete System

Mọi model kế thừa `BaseModel` đều có:
- `.delete()` — soft delete (đánh dấu, không xóa)
- `.hard_delete()` — xóa vĩnh viễn
- `.restore()` — khôi phục bản ghi đã soft delete

### 9. M2M Change Tracking

Thay đổi ManyToMany fields (`add`, `remove`, `clear`) được tự động theo dõi qua Django signals, cập nhật `updated_at`/`updated_by` và gửi thông báo cho superuser.

## Kiến trúc

```
django-whiteneuron/
├── whiteneuron/base/              # Core: models, admin, middleware
│   ├── models.py                  # User, BaseModel, Image, Mail, App, Blacklists
│   ├── admin.py                   # Custom admin classes cho tất cả models
│   └── middleware.py              # RateLimit, UserActivity, ThreadLocal, ...
├── whiteneuron/dashboard/         # Dashboard callback + KPI charts
├── whiteneuron/notification/      # WebSocket notifications
├── whiteneuron/file_management/   # File upload + integrity check
└── whiteneuron/feedbacks/         # Per-model feedback collection
```

## Yêu cầu hệ thống

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Python | >= 3.13 | Bắt buộc |
| Django | >= 6.0.6, < 7.0.0 | Django 6.0.x only |
| Redis | — | Cần cho rate limiting, blacklist cache, badge caching |
| Celery (tùy chọn) | — | Cho async tasks |

## Cài đặt nhanh

```bash
pip install django-whiteneuron
```

Thêm vào `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "whiteneuron",
    "whiteneuron.base",
    "whiteneuron.feedbacks",
    "whiteneuron.file_management",
    "whiteneuron.contrib",
    "whiteneuron.dashboard",
]

AUTH_USER_MODEL = "base.User"
```

Chạy migrations và bắt đầu:

```bash
python manage.py migrate
python manage.py runserver
```

## Ai nên dùng?

- **Django developers** cần admin panel đẹp, hiện đại với django-unfold
- **Admin teams** cần theo dõi hoạt động, thông báo real-time, rate limiting
- **SaaS platforms** cần quản lý file, feedback system, multi-language support
- **Projects** cần soft delete, audit trail, object-level permissions

## Liên hệ

- Email: [anhnt@whiteneuron.com](mailto:anhnt@whiteneuron.com)
- Website: [https://whiteneuron.ai](https://whiteneuron.ai)
- GitHub: [https://github.com/White-Neuron/django-whiteneuron](https://github.com/White-Neuron/django-whiteneuron)

## Giấy phép

MIT License. Tự do sử dụng, sửa đổi, phân phối cho mục đích cá nhân và thương mại.
