cd whiteneuron
mkdir -p locale

# Tạo symlink tạm trỏ vào package cần lấy chuỗi dịch từ .venv
ln -sfn ../.venv/lib/python3.11/site-packages/unfold _unfold_src

django-admin makemessages -l vi \
  --symlinks \
  --ignore "node_modules/*" \

# Xóa symlink sau khi xong
rm -f _unfold_src

cd ..