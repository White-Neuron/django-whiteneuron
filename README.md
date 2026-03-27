# django-whiteneuron

django-whiteneuron là package mở rộng Django Admin theo hướng hiện đại, tập trung vào UI/UX quản trị, dashboard, feedback, file management và các tích hợp admin nâng cao.

## Phiên bản hiện tại

- 0.2.27

## Tương thích

- Python >= 3.11
- Django >= 5.1.6
- django-unfold >= 0.84.0
- Tailwind CSS 4.x + daisyUI 5.x (khi dùng bộ style frontend đi kèm)

## Changelog

### v0.2.27 (2026-03-27)
- **Added**: Trường `action_by` vào model `Notification` — lưu thông tin user đã thực hiện hành động kích hoạt thông báo.
- **Added**: Migration `0009` thêm `action_by`, `0010`–`0011` cập nhật `related_name` và `verbose_name` của `Notification.user`.
- **Improved**: `display_changed_data` trong `NotificationAdmin` hỗ trợ parse cả JSON và Python literal, đúng schema `field_name/old_value/new_value`, escape XSS an toàn.
- **Improved**: `NotificationAdmin` hiển thị thêm `action_by` trong list, filter, search và form chi tiết.
- **Improved**: Badge trạng thái app trong grid view đổi từ text sang icon `check_circle`/`cancel` (Material Symbols) gọn hơn.
- **Improved**: Bản dịch tiếng Việt cập nhật entry mới: `Action By`, `User to Notify`, dọn dẹp các cờ `fuzzy` còn tồn đọng.
- **Fixed**: `action_by` được gán đúng trong tất cả các luồng tạo notification: `soft_delete`, `hard_delete`, `restore`, `delete_model`, và `BaseModel.save`.

### v0.2.26 (2026-03-23)
- **Fix**: Admin loading overlay no longer gets stuck during file downloads.
- **Added**: Backend-frontend handshake via `DownloadResponseFlagMiddleware` for robust download handling.
- **Improved**: Frontend loading logic with token-based polling and timeout guard (45s).
- **Improved**: Clean cookie reset on page visibility transitions.

### v0.2.25 và trước
Xem chi tiết tại [releases](https://github.com/White-Neuron/django-whiteneuron/releases).

## Cài đặt (ưu tiên uv)

Package chưa phát hành lên PyPI.

### Cài từ GitHub theo tag

```bash
uv add "git+https://github.com/White-Neuron/django-whiteneuron.git@v0.2.27"
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

Thêm middleware cần thiết:

```python
MIDDLEWARE = [
    "whiteneuron.base.middleware.ReadonlyExceptionHandlerMiddleware",
    "whiteneuron.base.middleware.UserActivityMiddleware",
    # ... middleware khác
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
    "SHOW_HISTORY": True,
    "SHOW_LANGUAGES": True,
    "DASHBOARD_CALLBACK": "whiteneuron.dashboard.views.dashboard_callback",
    "LOGIN": {
        "image": lambda request: static("base/images/login_bg.jpg"),
    },
    "STYLES": [
        lambda request: static("base/css/styles.css"),
        lambda request: static("base/css/btn-styles.css"),
        lambda request: static("base/css/loading.css"),
    ],
    "SCRIPTS": [
        lambda request: static("base/js/loading.js"),
    ],
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

## Môi trường cấu hình

Copy env.example thành file môi trường phù hợp cho dự án của bạn và cập nhật các biến như DATABASE, REDIS, EMAIL, ALLOWED_HOSTS.

## Liên hệ

- Email: [anhnt@whiteneuron.com](mailto:anhnt@whiteneuron.com)
- Website: [https://whiteneuron.ai](https://whiteneuron.ai)
- GitHub: [https://github.com/White-Neuron/django-whiteneuron](https://github.com/White-Neuron/django-whiteneuron)

## License

MIT License.
