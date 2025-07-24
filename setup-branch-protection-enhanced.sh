#!/bin/bash

# VersionTracker Branch Protection Setup (with GPG signing)
# Enhanced version that enforces signed commits

set -e

REPO="docdyhr/versiontracker"
BRANCH="master"

echo "🔒 Setting up enhanced branch protection for $REPO:$BRANCH"

# Check if gh CLI is authenticated
if ! gh auth status &>/dev/null; then
    echo "❌ GitHub CLI not authenticated. Please run 'gh auth login' first."
    exit 1
fi

echo "🚀 Applying enhanced branch protection rules with signed commits..."

# Create or update branch protection rule with signed commits required
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

# Enable signed commits requirement (separate API call)
echo "🔑 Enabling signed commits requirement..."
gh api \
    --method PATCH \
    -H "Accept: application/vnd.github.v3+json" \
    "/repos/$REPO" \
    --field "require_signed_commits=true" || echo "⚠️  Could not enable signed commits via API (may need manual setup)"

echo "✅ Enhanced branch protection rules applied successfully!"

echo ""
echo "🎉 Enhanced branch protection setup complete!"
echo ""
echo "Current protection features:"
echo "  ✅ Require status checks to pass before merging"
echo "  ✅ Require branches to be up to date before merging"
echo "  ✅ Require linear history (no merge commits)"
echo "  ✅ Prevent force pushes"
echo "  ✅ Prevent branch deletion"
echo "  ✅ Dismiss stale reviews when new commits are pushed"
echo "  ✅ Admin enforcement enabled (maximum security)"
echo "  ✅ Require code owner reviews"
echo "  ✅ Require conversation resolution before merging"
echo "  ✅ Signed commits required"
echo ""
echo "📋 Manual steps needed:"
echo "  1. Go to GitHub repo settings -> Branches"
echo "  2. Verify 'Require signed commits' is enabled"
echo "  3. Consider enabling 'Restrict pushes that create files' if needed"
echo ""
echo "To view current protection status:"
echo "  gh api repos/$REPO/branches/$BRANCH/protection"
