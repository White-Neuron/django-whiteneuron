echo "Building Tailwind CSS..."
bash scripts/tailwind.sh

echo "Make migrations..."
source .venv/bin/activate
cd whiteneuron
python manage.py makemigrations
cd ..

echo "Building package..."
uv build

read -p "Do you want to create a release? (y/n) " REPLY
echo
DATE=$(date)

if [[ $REPLY =~ ^[Yy]$ ]]; then
  # Get current version from pyproject.toml
  CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
  echo "Current version: $CURRENT_VERSION"
  
  read -p "Enter new version (or press Enter to keep $CURRENT_VERSION): " NEW_VERSION
  if [[ -z "$NEW_VERSION" ]]; then
    NEW_VERSION=$CURRENT_VERSION
  fi
  
  # Update version in pyproject.toml if changed
  if [[ "$NEW_VERSION" != "$CURRENT_VERSION" ]]; then
    sed -i '' "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
    echo "Updated version to: $NEW_VERSION"
    
    # Rebuild with new version
    echo "Rebuilding package with new version..."
    uv build
  fi
  
  read -p "Enter release message: " MESSAGE
  
  echo "Creating release v$NEW_VERSION with message: $MESSAGE"
  
  # Commit changes
  git add .
  git commit -m "Release v$NEW_VERSION: $MESSAGE"
  
  # Create and push tag
  git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION: $MESSAGE"
  
  # Push to GitHub
  git push origin $(git branch --show-current)
  git push origin "v$NEW_VERSION"
  
  echo "✅ Release v$NEW_VERSION created successfully!"
  echo "🔗 Check your release at: https://github.com/White-Neuron/django-whiteneuron/releases"
else
  echo "Build completed without release."
fi

echo "Done!"
