#!/bin/bash

# Release script for ExplainB Action
set -e

VERSION_FILE="VERSION"
CHANGELOG_FILE="CHANGELOG.md"

# Check if VERSION file exists
if [ ! -f "$VERSION_FILE" ]; then
    echo "❌ Error: VERSION file not found"
    exit 1
fi

# Read version
VERSION=$(cat $VERSION_FILE | tr -d '\n')
echo "🚀 Preparing release for version: v$VERSION"

# Check if we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Warning: Not on main branch (current: $CURRENT_BRANCH)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Release cancelled"
        exit 1
    fi
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "❌ Error: You have uncommitted changes"
    echo "Please commit or stash your changes before releasing"
    exit 1
fi

# Check if tag already exists
if git tag -l | grep -q "^v$VERSION$"; then
    echo "❌ Error: Tag v$VERSION already exists"
    exit 1
fi

echo "📋 Release checklist:"
echo "   ✅ Version: v$VERSION"
echo "   ✅ Branch: $CURRENT_BRANCH"
echo "   ✅ Working directory clean"
echo "   ✅ Tag v$VERSION does not exist"
echo ""

# Confirm release
read -p "🚀 Create release v$VERSION? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Release cancelled"
    exit 1
fi

# Create and push tag
echo "🏷️  Creating tag v$VERSION..."
git tag -a "v$VERSION" -m "Release v$VERSION

$(cat RELEASE_NOTES.md | head -20)

See CHANGELOG.md for full details."

echo "📤 Pushing tag to origin..."
git push origin "v$VERSION"

echo ""
echo "✅ Release v$VERSION created successfully!"
echo ""
echo "🌐 Next steps:"
echo "   1. Go to GitHub repository"
echo "   2. Create a new release from tag v$VERSION"
echo "   3. Copy release notes from RELEASE_NOTES.md"
echo "   4. Publish the release"
echo ""
echo "📄 Tag created: v$VERSION"
echo "🔗 GitHub releases: https://github.com/BohuTANG/explainb-action/releases"