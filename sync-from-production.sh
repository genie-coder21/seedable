#!/bin/bash
# Sync script to copy code changes from production (/opt/seedable) to GitHub version
# This keeps personal credentials separate while syncing code changes

PROD_DIR="/opt/seedable"
GITHUB_DIR="/mnt/expansion/github/seedable"

echo "Syncing code from $PROD_DIR to $GITHUB_DIR..."
echo ""

# Files that are safe to sync (no personal data)
SAFE_FILES=(
    "seedable.py"
    "Dockerfile"
    "requirements.txt"
    "README.md"
    ".gitignore"
)

# Copy safe files
for file in "${SAFE_FILES[@]}"; do
    if [ -f "$PROD_DIR/$file" ]; then
        echo "Copying $file..."
        cp "$PROD_DIR/$file" "$GITHUB_DIR/$file"
    else
        echo "Warning: $file not found in $PROD_DIR"
    fi
done

echo ""
echo "Sync complete! Files copied:"
echo "  - seedable.py (main application code)"
echo "  - Dockerfile"
echo "  - requirements.txt"
echo "  - README.md"
echo "  - .gitignore"
echo ""
echo "NOT copied (contains personal data):"
echo "  - docker-compose.yml (contains API keys and IP addresses)"
echo "  - .env files"
echo ""
echo "Next steps:"
echo "  1. Review changes: cd $GITHUB_DIR && git diff"
echo "  2. Commit changes: git add . && git commit -m 'Your message'"
echo "  3. Push to GitHub: git push"
