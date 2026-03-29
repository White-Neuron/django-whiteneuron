# django-whiteneuron

django-whiteneuron là package mở rộng Django Admin theo hướng hiện đại, tập trung vào UI/UX quản trị, dashboard, feedback, file management và các tích hợp admin nâng cao.

## Phiên bản hiện tại

- 0.2.35

## Tương thích

- Python >= 3.11
- Django >= 5.1.6
- django-unfold >= 0.85.0
- Tailwind CSS 4.x + daisyUI 5.x (khi dùng bộ style frontend đi kèm)

## Changelog

### v0.2.35 (2026-03-29) — latest
**Dynamic IP Blacklist: Redis + Model + Admin**
- **Added**: `IPBlacklist` model (`base/ip_blacklists`) — quản lý IP bị chặn real-time qua Django Admin, hỗ trợ block vĩnh viễn và tạm thời (`blocked_until` với Redis TTL tự expire).
- **Added**: `IPBlacklistAdmin` — giao diện quản lý IP blacklist với actions Activate/Deactivate, hiện thị trong sidebar System dưới icon `block`, superuser only.
- **Added**: Action **"Block IP address"** trong `UserActivityAdmin` — chọn bản ghi activity → block IP ngay lập tức vào Redis, không cần restart Daphne.
- **Improved**: `RateLimitMiddleware._is_blacklisted()` kiểm tra thêm `cache.get('blacklist:dynamic:<ip>')` sau static env blacklist — hybrid hai lớp tĩnh + động.
- **Added**: Migration `base/0015_ipblacklist.py`.

### v0.2.34 (2026-03-29)
**IP Blacklist: chặn IP/CIDR vĩnh viễn qua `.env`**
- **Added**: `RateLimitMiddleware` bổ sung `_is_blacklisted()` — kiểm tra IP/CIDR blacklist trước rate limit, trả 403 ngay lập tức cho IP bị block.
- **Added**: Parse `IP_BLACKLIST` từ settings (comma-separated IPs và/hoặc CIDR), hỗ trợ cả IPv4 và IPv6 — single IP dùng `set` lookup O(1), CIDR range dùng `ip_network` match.
- **Added**: Setting `IP_BLACKLIST` trong `settings.py` và biến tương ứng trong `env.example`.

### v0.2.33 (2026-03-29)
**Rate Limiting fix cho Docker + Daphne**
- **Fixed**: `_is_rate_limited()` và `_is_user_rate_limited()` thêm `except Exception: return False` — bắt `ConnectionError` khi Redis không reachable trong Docker (trước đây unhandled exception làm request crash hoặc bypass rate limit).
- **Fixed**: Default `RATE_LIMIT_REQUESTS` hạ từ 300 → 60 req/60 s, `USER_RATE_LIMIT_REQUESTS` từ 200 → 60 — phù hợp với admin panel.
- **Fixed**: `User.display_header()` dùng `reverse('admin:base_user_change')` thay vì hardcode `/admin/base/user/` — tránh broken link khi đổi admin prefix.
- **Fixed**: Default `BEHIND_CLOUDFLARE=True` vì luôn deploy qua Cloudflare Tunnel.

### v0.2.32 (2026-03-29)
**Security hardening & Gunicorn production readiness**
- **Security**: `get_client_ip()` chỉ tin tưởng `CF-Connecting-IP` / `True-Client-IP` khi `BEHIND_CLOUDFLARE=True` — tránh bypass rate limit qua header giả mạo.
- **Fixed**: `UserActivityMiddleware.__call__()` cache kết quả `do_not_track()` vào `skip` — tránh gọi 2 lần mỗi request.
- **Removed**: `import logging` không dùng trong middleware.py.

### v0.2.31 (2026-03-29)
**Rate Limiting, Security Hardening & Error Pages**
- **Added**: `RateLimitMiddleware` — global IP-based rate limiting (300 req/60 s mặc định) đặt ngay sau `SecurityMiddleware`, hoạt động cả trên API lẫn browser.
- **Improved**: `UserActivityMiddleware` bổ sung per-user rate limiting (200 req/60 s mặc định).
- **Added**: `/ws/` vào `exclude_paths` của `UserActivityMiddleware` — WS handshake không bị log và không tính vào rate limit.
- **Security**: Sanitize `POST` data trước khi ghi vào `UserActivity` — mask các field nhạy cảm (password, token, api_key…).
- **Security**: Chuyển sang pattern `cache.incr()` first (atomic trên Redis) tránh race condition.
- **Added**: Template lỗi đầy đủ: `400.html`, `403.html`, `404.html`, `429.html`, `500.html`.
- **Added**: `base.html` skeleton tối giản cho các trang lỗi — không phụ thuộc file static ngoài.
- **Added**: Cảnh báo startup khi production chạy không có Redis (rate limit không chính xác trên multi-worker).

### v0.2.30 (2026-03-29)
- **Improved**: `AppAdmin.get_queryset()` chỉ trả về các app active mà user thực sự có quyền truy cập.
- **Improved**: `superuser` vẫn giữ nguyên quyền nhìn thấy toàn bộ app active.

### v0.2.29 (2026-03-28)
- **Fixed**: `NotificationAdmin` không còn bị lỗi 403 khi bấm `View Linked Object`.
- **Improved**: Action xem đối tượng liên kết được route riêng qua detail action, tương thích tốt hơn với Unfold.
- **Improved**: Bổ sung xử lý an toàn khi notification không có `obj_link`.

### v0.2.28 (2026-03-28)
- **Improved**: Giao diện grid view của user/app dùng icon trực quan hơn cho role và trạng thái.
- **Improved**: Chuẩn hóa `verbose_name` cho nhiều field trong `Notification` và `NotificationConfig`.
- **Added**: Migration `notification/0012` đồng bộ metadata field-level.

### v0.2.27 và trước
Xem chi tiết tại [releases](https://github.com/White-Neuron/django-whiteneuron/releases).

## Cài đặt (ưu tiên uv)

Package chưa phát hành lên PyPI.

### Cài từ GitHub theo tag

```bash
uv add "git+https://github.com/White-Neuron/django-whiteneuron.git@v0.2.35"
```

### Cài từ source local

```bash
uv pip install -e .
```

## Cấu hình Django cơ bản

Thêm các app vào đầu INSTALLED_APPS:

```python
INSTALLED_APPS = [
    "whiteneuron",
    "whiteneuron.base",
    "whiteneuron.feedbacks",
    "whiteneuron.file_management",
    "whiteneuron.contrib",
    "whiteneuron.dashboard",
    # ... các app khác
]
```

Thêm middleware cần thiết (thứ tự quan trọng):

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whiteneuron.base.middleware.RateLimitMiddleware",   # ← ngay sau SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whiteneuron.base.middleware.ReadonlyExceptionHandlerMiddleware",
    "whiteneuron.base.middleware.UserActivityMiddleware",  # ← sau AuthenticationMiddleware
    "whiteneuron.base.middleware.ThreadLocalMiddleware",
]
```

Thiết lập user model:

```python
AUTH_USER_MODEL = "base.User"
```

## Cấu hình UNFOLD mẫu

```python
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_HEADER": _("White Neuron"),
    "SITE_TITLE": _("White Neuron Admin"),
    "SITE_SUBHEADER": _("Admin panel"),
    # Dùng SITE_ICON thay vì SITE_LOGO để giữ SITE_TITLE hiển thị đúng
    "SITE_ICON": {
        "light": lambda request: static("base/images/logo/WhiteNeuron.png"),
        "dark": lambda request: static("base/images/logo/WhiteNeuron.png"),
    },
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("base/images/logo/WhiteNeuron.png"),
        },
    ],
    "SHOW_HISTORY": False,
    "SHOW_LANGUAGES": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "DASHBOARD_CALLBACK": "whiteneuron.dashboard.views.dashboard_callback",
    "LOGIN": {
        "image": lambda request: static("base/images/login-bg.jpg"),
    },
    "STYLES": [
        lambda request: static("base/css/styles.css"),
        lambda request: static("base/css/btn-styles.css"),
        lambda request: static("base/css/loading.css"),
    ],
    "SCRIPTS": [
        lambda request: static("base/js/loading.js"),
        lambda request: static("base/js/whiteneuron.js"),
    ],
    "BORDER_RADIUS": "6px",
}
```

## Frontend (Tailwind 4 + daisyUI 5)

Cài dependencies frontend:

```bash
npm install -D @tailwindcss/cli@next daisyui@latest
```

Build CSS bằng script có sẵn:

```bash
bash scripts/tailwind.sh
```

Hoặc chạy trực tiếp:

```bash
npx @tailwindcss/cli -i styles.css -o whiteneuron/static/base/css/styles.css --minify
```

## Chạy local package example

```bash
cd whiteneuron
python manage.py migrate
python manage.py runserver
```

Truy cập admin tại: http://127.0.0.1:8000/admin/

## Build package

```bash
uv build
```

Hoặc dùng script build tổng hợp:

```bash
bash scripts/build.sh
```

## Rate Limiting

`RateLimitMiddleware` giới hạn theo IP, `UserActivityMiddleware` giới hạn theo user đã đăng nhập. Cần Redis để hoạt động chính xác trên môi trường multi-worker.

```python
# settings.py (hoặc env)
RATE_LIMIT_REQUESTS = 60   # số request tối đa / window (theo IP)
RATE_LIMIT_WINDOW    = 60   # tính bằng giây

USER_RATE_LIMIT_REQUESTS = 60  # theo user đã đăng nhập
USER_RATE_LIMIT_WINDOW   = 60
```

Các biến env tương ứng: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`, `USER_RATE_LIMIT_REQUESTS`, `USER_RATE_LIMIT_WINDOW`.

Khi vượt ngưỡng:
- Request API (`/api/` hoặc `Accept: application/json`) → JSON `{"detail": "Too many requests."}` với status 429.
- Request browser → render template `429.html` với header `Retry-After`.

## IP Blacklist

Hai lớp bảo vệ hoạt động song song. Cả hai đều được kiểm tra trước rate limit, trả 403 ngay lập tức.

### Tĩnh — `.env` (CIDR ranges, infra bans)

Load lúc khởi động, hỗ trợ IPv4/IPv6 và CIDR:

```env
# .env
IP_BLACKLIST=185.220.101.5,194.165.16.0/22,2001:db8::/32
```

Cần **restart Daphne/Gunicorn** để apply khi thêm entry mới.

### Động — Django Admin + Redis (real-time)

Quản lý qua **System → IP Blacklist** trong admin panel (superuser only):

- **Block vĩnh viễn**: để trống `blocked_until`
- **Block tạm thời**: set `blocked_until` → Redis TTL tự expire, không cần cron
- **Block nhanh từ logs**: *User Activity* → chọn records → action **Block IP address** → Redis key set ngay, không restart

```
Request → check static env blacklist (O(1))
        → check cache.get('blacklist:dynamic:<ip>') (1 Redis GET)
        → 403 nếu match, không tốn rate limit check
```

## Error Pages

Các template lỗi nằm trong `whiteneuron/templates/` và được Django tự động sử dụng khi `DEBUG=False`:

| Template | Lỗi | Ghi chú |
|---|---|---|
| `400.html` | Bad Request | |
| `403.html` | Forbidden | |
| `404.html` | Not Found | |
| `429.html` | Too Many Requests | Render thủ công bởi middleware, truyền `{{ retry_after }}` |
| `500.html` | Server Error | |

Không cần đăng ký `handler400/403/404/500` — Django tự tìm template qua `APP_DIRS=True`.

## Môi trường cấu hình

Copy env.example thành file môi trường phù hợp cho dự án của bạn và cập nhật các biến như DATABASE, REDIS, EMAIL, ALLOWED_HOSTS.

## Liên hệ

- Email: [anhnt@whiteneuron.com](mailto:anhnt@whiteneuron.com)
- Website: [https://whiteneuron.ai](https://whiteneuron.ai)
- GitHub: [https://github.com/White-Neuron/django-whiteneuron](https://github.com/White-Neuron/django-whiteneuron)

## License

MIT License.
