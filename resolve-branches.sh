#!/bin/bash

# VersionTracker Branch Resolution Script
# Identifies and resolves common branch configuration issues

set -e

REPO="docdyhr/versiontracker"
echo "🔍 Analyzing branch configuration for $REPO"

# Function to check current branch status
check_branch_status() {
    echo "📊 Current Branch Status:"
    echo "   Local branch: $(git branch --show-current)"
    echo "   Remote branches:"
    git branch -r | head -10
    echo ""
}

# Function to check protection status
check_protection_status() {
    echo "🔒 Checking branch protection status..."

    # Check master branch protection
    if gh api "repos/$REPO/branches/master/protection" &>/dev/null; then
        echo "✅ Master branch protection is active"
    else
        echo "❌ Master branch protection not found"
    fi

    # Check main branch protection
    if gh api "repos/$REPO/branches/main/protection" &>/dev/null; then
        echo "✅ Main branch protection is active"
    else
        echo "⚠️  Main branch protection not found"
    fi
    echo ""
}

# Function to identify the default branch
identify_default_branch() {
    echo "🎯 Identifying default branch..."

    local default_branch
    default_branch=$(gh api "repos/$REPO" --jq '.default_branch')
    echo "   GitHub default branch: $default_branch"

    local local_branch
    local_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "unknown")
    echo "   Local tracking branch: $local_branch"

    # Check if they match
    if [[ "$default_branch" == "$local_branch" ]]; then
        echo "✅ Branch configuration is consistent"
    else
        echo "⚠️  Branch configuration mismatch detected"
        echo "   Recommendation: Update local tracking or GitHub default"
    fi

    echo ""
    echo "DEFAULT_BRANCH=$default_branch" > .branch-config
}

# Function to resolve branch protection issues
resolve_protection_issues() {
    local default_branch=$1
    echo "🔧 Resolving branch protection for: $default_branch"

    # Update the branch protection script with correct branch
    if [[ -f "setup-branch-protection.sh" ]]; then
        sed -i '' "s/BRANCH=\".*\"/BRANCH=\"$default_branch\"/" setup-branch-protection.sh
        echo "✅ Updated setup-branch-protection.sh to use '$default_branch'"
    fi

    # Apply protection rules to the correct branch
    echo "🚀 Applying protection rules to '$default_branch'..."

    gh api \
        --method PUT \
        -H "Accept: application/vnd.github.v3+json" \
        "/repos/$REPO/branches/$default_branch/protection" \
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

    echo "✅ Branch protection applied successfully!"
}

# Function to update local git configuration
update_local_config() {
    local default_branch=$1
    echo "🔄 Updating local git configuration..."

    # Update remote HEAD reference
    git remote set-head origin "$default_branch"
    echo "✅ Updated local remote HEAD to track '$default_branch'"

    # Switch to default branch if not already there
    local current_branch
    current_branch=$(git branch --show-current)

    if [[ "$current_branch" != "$default_branch" ]]; then
        echo "🔀 Switching from '$current_branch' to '$default_branch'"
        git checkout "$default_branch"
        git pull origin "$default_branch"
    fi
}

# Function to check workflow files for branch references
check_workflow_branches() {
    echo "🔍 Checking GitHub Actions workflows for branch references..."

    local issues_found=false

    if [[ -d ".github/workflows" ]]; then
        for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
            if [[ -f "$workflow" ]]; then
                if grep -q "branches.*master" "$workflow" 2>/dev/null; then
                    echo "⚠️  Found 'master' reference in: $workflow"
                    issues_found=true
                fi
                if grep -q "branches.*main" "$workflow" 2>/dev/null; then
                    echo "ℹ️  Found 'main' reference in: $workflow"
                fi
            fi
        done
    fi

    if [[ "$issues_found" == true ]]; then
        echo "📝 Consider updating workflow files to use consistent branch naming"
    else
        echo "✅ Workflow files appear to have consistent branch references"
    fi
}

# Main execution
main() {
    echo "🚀 Starting branch resolution process..."
    echo ""

    # Check authentication
    if ! gh auth status &>/dev/null; then
        echo "❌ GitHub CLI not authenticated. Please run 'gh auth login' first."
        exit 1
    fi

    # Perform checks
    check_branch_status
    check_protection_status
    identify_default_branch

    # Load the identified default branch
    # shellcheck disable=SC1091
    source .branch-config

    # Check workflow consistency
    check_workflow_branches

    echo "🎯 Resolution Actions:"
    echo ""

    # Resolve protection issues
    resolve_protection_issues "$DEFAULT_BRANCH"
    echo ""

    # Update local configuration
    update_local_config "$DEFAULT_BRANCH"
    echo ""

    # Final verification
    echo "✅ Branch resolution complete!"
    echo ""
    echo "📋 Summary:"
    echo "   • Default branch: $DEFAULT_BRANCH"
    echo "   • Branch protection: Active"
    echo "   • Local tracking: Updated"
    echo "   • Protection script: Updated"
    echo ""
    echo "🔗 Verify at: https://github.com/$REPO/settings/branches"

    # Clean up
    rm -f .branch-config
}

# Run main function
main
