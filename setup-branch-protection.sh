#!/bin/bash

# VersionTracker Branch Protection Setup
# Sets up branch protection rules for solo development following best practices

set -e

REPO="docdyhr/versiontracker"
BRANCH="master"

echo "🔒 Setting up branch protection for $REPO:$BRANCH"

# Check if gh CLI is authenticated
if ! gh auth status &>/dev/null; then
    echo "❌ GitHub CLI not authenticated. Please run 'gh auth login' first."
    exit 1
fi

# Check if GPG signing is configured
if git config --get user.signingkey &>/dev/null; then
    echo "✅ GPG signing key detected"
else
    echo "⚠️  No GPG signing key found. Consider setting up commit signing for better security."
    echo "    You can set it up with: git config --global user.signingkey <your-key-id>"
    echo "    And enable signing with: git config --global commit.gpgsign true"
fi

echo "🚀 Applying branch protection rules..."

# Create or update branch protection rule
# For solo development, we balance security with flexibility
gh api \
    --method PUT \
    -H "Accept: application/vnd.github.v3+json" \
    "/repos/$REPO/branches/$BRANCH/protection" \
    --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Test Python 3.10 on ubuntu-latest",
      "Test Python 3.11 on ubuntu-latest",
      "Test Python 3.12 on ubuntu-latest",
      "Test Python 3.10 on macos-latest",
      "Test Python 3.11 on macos-latest",
      "Test Python 3.12 on macos-latest",
      "lint / lint",
      "security / security-scan"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
EOF

echo "✅ Branch protection rules applied successfully!"

# Additional security recommendations
echo ""
echo "🔧 Additional Security Recommendations:"
echo "   • Consider enabling 'Require signed commits' in GitHub repo settings"
echo "   • Enable 'Require administrators to follow these rules' for maximum security"
echo "   • Consider adding CODEOWNERS file for automatic review assignments"
echo "   • Enable Dependabot security updates in repository settings"

# Create a CODEOWNERS file if it doesn't exist
if [ ! -f ".github/CODEOWNERS" ]; then
    echo ""
    echo "📝 Creating CODEOWNERS file for better review management..."
    mkdir -p .github
    cat > .github/CODEOWNERS <<'EOL'
# Global owner for all files
* @docdyhr

# Python core files require extra attention
*.py @docdyhr
pyproject.toml @docdyhr
requirements*.txt @docdyhr

# Configuration and CI/CD files
.github/ @docdyhr
*.yml @docdyhr
*.yaml @docdyhr

# Security-sensitive files
SECURITY.md @docdyhr
LICENSE @docdyhr
EOL
    echo "✅ CODEOWNERS file created"
fi

echo ""
echo "🎉 Branch protection setup complete!"
echo ""
echo "Current protection features:"
echo "  ✅ Require status checks to pass before merging"
echo "  ✅ Require branches to be up to date before merging"
echo "  ✅ Require linear history (no merge commits)"
echo "  ✅ Prevent force pushes"
echo "  ✅ Prevent branch deletion"
echo "  ✅ Dismiss stale reviews when new commits are pushed"
echo "  ✅ Admin enforcement enabled (maximum security)"
echo "  ✅ Code owner reviews required"
echo "  ✅ Conversation resolution required before merging"
echo ""
echo "To view current protection status:"
echo "  gh api repos/$REPO/branches/$BRANCH/protection"
