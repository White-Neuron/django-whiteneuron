# Phân tích rủi ro nâng cấp Django Unfold (v0.72 -> v0.76)

Sau khi đối chiếu code hiện tại của project với các thay đổi từ upstream, dưới đây là các điểm xung đột (conflict) cụ thể cần xử lý thủ công.

## 1. 🚨 Rủi ro cao (Breaking Changes)

### 1.1 `navigation_user.html` - Lỗi Custom User Model
- **File:** `whiteneuron/templates/unfold/helpers/navigation_user.html`
- **Vấn đề:**
  File hiện tại đang dùng `user.username`:
  ```django
  {{ user.get_full_name|default:user.username }}
  ```
  Trong version **0.75.0**, upstream đã đổi sang `user.get_username` để hỗ trợ custom user model (ví dụ login bằng email/phone mà không có field `username`).
- **Nguy cơ:** Nếu project dùng Custom User Model không có field `username`, trang admin sẽ bị **Crash 500**.
- **Cách fix:**
  Sửa dòng 27 thành:
  ```django
  {{ user.get_full_name|default:user.get_username }}
  ```

### 1.2 `change_list.html` - Xung đột giao diện Actions Bar và Filters
- **File:** `whiteneuron/templates/admin/change_list.html`
- **Vấn đề:**
  - Bạn đang override block `result_list` và tự include `unfold/helpers/change_list_actions.html`.
  - Version **0.74.0** đã redesign lại toàn bộ thanh actions (CSS, layout flexbox mới).
  - Version **0.76.0** thay đổi cách ẩn/hiện topbar khi không có filter.
- **Nguy cơ:**
  - Các nút actions (xóa, update hàng loạt) có thể bị vỡ layout, dính vào nhau hoặc không hiển thị menu dropdown đúng cách.
  - Grid view (`.grid_view`) có thể bị conflict CSS với thanh actions mới.
- **Hành động:**
  - Cần test kỹ màn hình danh sách (Change List) khi chọn nhiều dòng.
  - Kiểm tra xem nút "Go" hoặc dropdown actions có bị che khuất không.

## 2. ⚠️ Rủi ro trung bình (UI/UX)

### 2.1 `account_links.html` - Modal Logout & User Links
- **File:** `whiteneuron/templates/unfold/helpers/account_links.html`
- **Vấn đề:**
  - Code hiện tại đang dùng cơ chế Modal riêng của bạn (`x-data="{ openUserLinks: false }"` và backdrop mờ).
  - Version **0.73.0** upstream đã thay đổi cấu trúc menu user để đưa vào sidebar.
- **Nguy cơ:**
  - Không gây crash, nhưng logic `skip_auto_guest` cookie hoặc giao diện modal có thể trông lạc quẻ so với theme mới của 0.76.
  - Nút "Logout" trong sidebar mới (của theme 0.76) có thể hoạt động song song hoặc thừa thãi so với modal này.

### 2.2 `app_list_badge.html` (Nếu có dùng)
- Upstream có thể đã update CSS classes cho badge (màu sắc, spacing). Cần kiểm tra xem badge số lượng (nếu có) còn hiển thị đẹp không.

---

## 3. Kế hoạch Merge & Fix

1. **Bước 1:** Update package:
   `pip install django-unfold==0.76.0`
2. **Bước 2 (Hotfix ngay):**
   Sửa `navigation_user.html` thay `.username` -> `.get_username`.
3. **Bước 3 (Test UI):**
   - Vào trang danh sách User -> Chọn vài dòng -> Kiểm tra Actions dropdown.
   - Bấm vào Avatar -> Kiểm tra Modal Account Links.
