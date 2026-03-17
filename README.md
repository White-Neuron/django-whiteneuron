# django-whiteneuron

django-whiteneuron là package mở rộng Django Admin theo hướng hiện đại, tập trung vào UI/UX quản trị, dashboard, feedback, file management và các tích hợp admin nâng cao.

## Phiên bản hiện tại

- 0.2.24

## Tương thích

- Python >= 3.11
- Django >= 5.1.6
- django-unfold >= 0.84.0
- Tailwind CSS 4.x + daisyUI 5.x (khi dùng bộ style frontend đi kèm)

## Cài đặt (ưu tiên uv)

Package chưa phát hành lên PyPI.

### Cài từ GitHub theo tag

```bash
uv add "git+https://github.com/White-Neuron/django-whiteneuron.git@v0.2.24"
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
