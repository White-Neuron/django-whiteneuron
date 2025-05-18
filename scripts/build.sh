echo "Building Tailwind CSS..."
bash .scripts/tailwind.sh
echo "Building package..."
uv build
read -p "Do you want to push to Github? (y/n) " REPLY
echo
DATE=$(date)
if [[ $REPLY =~ ^[Yy]$ ]]; then
  read -p "Enter commit message: " MESSAGE
  echo "Pushing to Github with message: $MESSAGE"
  git add .
  git commit -m "Build $DATE: $MESSAGE"
  git push
fi
echo "Done!"
