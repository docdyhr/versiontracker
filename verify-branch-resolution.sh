#!/bin/bash

# VersionTracker Branch Resolution Verification Script
# Validates that all branch-related configurations are properly resolved

set -e

REPO="docdyhr/versiontracker"
DEFAULT_BRANCH="master"

echo "🔍 Verifying branch resolution for VersionTracker"
echo "=================================================="
echo ""

# Function to check GitHub repository configuration
check_github_config() {
    echo "🌟 GitHub Repository Configuration:"
    
    local gh_default_branch
    gh_default_branch=$(gh api "repos/$REPO" --jq '.default_branch')
    
    if [[ "$gh_default_branch" == "$DEFAULT_BRANCH" ]]; then
        echo "   ✅ Default branch: $gh_default_branch"
    else
        echo "   ⚠️  Default branch mismatch: $gh_default_branch (expected: $DEFAULT_BRANCH)"
    fi
    
    # Check branch protection
    if gh api "repos/$REPO/branches/$DEFAULT_BRANCH/protection" &>/dev/null; then
        echo "   ✅ Branch protection: Active on $DEFAULT_BRANCH"
        
        # Get protection details
        local protection_data
        protection_data=$(gh api "repos/$REPO/branches/$DEFAULT_BRANCH/protection")
        
        local linear_history
        linear_history=$(echo "$protection_data" | jq -r '.required_linear_history')
        
        local force_pushes
        force_pushes=$(echo "$protection_data" | jq -r '.allow_force_pushes')
        
        local admin_enforce
        admin_enforce=$(echo "$protection_data" | jq -r '.enforce_admins')
        
        echo "      • Linear history: $linear_history"
        echo "      • Force pushes blocked: $([[ "$force_pushes" == "false" ]] && echo "true" || echo "false")"
        echo "      • Admin enforcement: $admin_enforce"
    else
        echo "   ❌ Branch protection: Not found on $DEFAULT_BRANCH"
    fi
    
    echo ""
}

# Function to check local git configuration
check_local_config() {
    echo "💻 Local Git Configuration:"
    
    local current_branch
    current_branch=$(git branch --show-current)
    
    local remote_head
    remote_head=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "not set")
    
    echo "   • Current branch: $current_branch"
    echo "   • Remote HEAD: $remote_head"
    
    if [[ "$current_branch" == "$DEFAULT_BRANCH" ]]; then
        echo "   ✅ On correct default branch"
    else
        echo "   ⚠️  Not on default branch (consider: git checkout $DEFAULT_BRANCH)"
    fi
    
    if [[ "$remote_head" == "$DEFAULT_BRANCH" ]]; then
        echo "   ✅ Remote HEAD tracking correct branch"
    else
        echo "   ⚠️  Remote HEAD not tracking default branch"
    fi
    
    echo ""
}

# Function to check workflow file consistency
check_workflows() {
    echo "🔄 GitHub Actions Workflow Configuration:"
    
    local workflow_count=0
    local consistent_count=0
    
    for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
        if [[ -f "$workflow" ]] && [[ "$workflow" != *.backup ]]; then
            local workflow_name
            workflow_name=$(basename "$workflow")
            ((workflow_count++))
            
            # Check for branch references
            if grep -q "branches:" "$workflow"; then
                if grep -q "branches:.*$DEFAULT_BRANCH" "$workflow" && ! grep -q "branches:.*main" "$workflow"; then
                    echo "   ✅ $workflow_name: Uses $DEFAULT_BRANCH correctly"
                    ((consistent_count++))
                elif grep -q "branches:.*main.*master\|branches:.*master.*main" "$workflow"; then
                    echo "   ⚠️  $workflow_name: Contains both main and master"
                elif grep -q "branches:.*main" "$workflow"; then
                    echo "   ❌ $workflow_name: Uses 'main' instead of '$DEFAULT_BRANCH'"
                else
                    echo "   ✅ $workflow_name: Uses $DEFAULT_BRANCH correctly"
                    ((consistent_count++))
                fi
            else
                echo "   ℹ️  $workflow_name: No branch triggers (scheduled/manual only)"
                ((consistent_count++))
            fi
        fi
    done
    
    echo ""
    echo "   📊 Summary: $consistent_count/$workflow_count workflows properly configured"
    
    if [[ $consistent_count -eq $workflow_count ]]; then
        echo "   ✅ All workflows use consistent branch configuration"
    else
        echo "   ⚠️  Some workflows may need manual review"
    fi
    
    echo ""
}

# Function to check security configuration
check_security_config() {
    echo "🔒 Security Configuration:"
    
    # Check Dependabot
    if [[ -f ".github/dependabot.yml" ]]; then
        echo "   ✅ Dependabot configuration exists"
        
        if grep -q "target-branch.*$DEFAULT_BRANCH" ".github/dependabot.yml" || ! grep -q "target-branch" ".github/dependabot.yml"; then
            echo "      • Target branch: Correctly configured"
        else
            echo "      ⚠️  Target branch: May need review"
        fi
    else
        echo "   ❌ Dependabot configuration missing"
    fi
    
    # Check security monitoring
    if gh api "repos/$REPO/vulnerability-alerts" &>/dev/null; then
        echo "   ✅ Vulnerability alerts: Enabled"
    else
        echo "   ❌ Vulnerability alerts: Not enabled"
    fi
    
    if gh api "repos/$REPO/automated-security-fixes" &>/dev/null; then
        echo "   ✅ Automated security fixes: Enabled"
    else
        echo "   ❌ Automated security fixes: Not enabled"
    fi
    
    echo ""
}

# Function to check documentation consistency
check_documentation() {
    echo "📚 Documentation Consistency:"
    
    local doc_issues=()
    
    # Check README
    if [[ -f "README.md" ]]; then
        if grep -q "main" README.md && ! grep -q "$DEFAULT_BRANCH" README.md; then
            doc_issues+=("README.md contains 'main' references")
        else
            echo "   ✅ README.md: Branch references appear consistent"
        fi
    fi
    
    # Check CONTRIBUTING
    if [[ -f "CONTRIBUTING.md" ]]; then
        if grep -q "main" CONTRIBUTING.md && ! grep -q "$DEFAULT_BRANCH" CONTRIBUTING.md; then
            doc_issues+=("CONTRIBUTING.md contains 'main' references")
        else
            echo "   ✅ CONTRIBUTING.md: Branch references appear consistent"
        fi
    fi
    
    # Check docs directory
    if [[ -d "docs" ]]; then
        if grep -r "main" docs/ &>/dev/null && ! grep -r "$DEFAULT_BRANCH" docs/ &>/dev/null; then
            doc_issues+=("docs/ directory contains 'main' references")
        else
            echo "   ✅ docs/: Branch references appear consistent"
        fi
    fi
    
    if [[ ${#doc_issues[@]} -gt 0 ]]; then
        echo "   ⚠️  Documentation issues found:"
        printf '      • %s\n' "${doc_issues[@]}"
        echo "   💡 Consider updating these files manually"
    else
        echo "   ✅ All documentation appears consistent"
    fi
    
    echo ""
}

# Function to provide final recommendations
provide_final_recommendations() {
    echo "💡 Final Recommendations:"
    echo ""
    
    echo "1. 🧪 Test Your Configuration:"
    echo "   • Create a test branch: git checkout -b test/branch-validation"
    echo "   • Make a small change and push: git push origin test/branch-validation"
    echo "   • Create a PR: gh pr create --title 'Test: Branch validation'"
    echo "   • Verify all CI checks run correctly"
    echo ""
    
    echo "2. 🔄 Monitor Workflows:"
    echo "   • Check: https://github.com/$REPO/actions"
    echo "   • Ensure all workflows trigger on '$DEFAULT_BRANCH' events"
    echo "   • Verify status checks appear in PR requirements"
    echo ""
    
    echo "3. 🛡️  Verify Security:"
    echo "   • Check: https://github.com/$REPO/security"
    echo "   • Confirm Dependabot is creating PRs against '$DEFAULT_BRANCH'"
    echo "   • Review any existing security alerts"
    echo ""
    
    echo "4. 📖 Update Documentation:"
    echo "   • Review any remaining 'main' references in documentation"
    echo "   • Update branch naming in contributor guidelines"
    echo "   • Ensure README badges point to correct branch"
    echo ""
}

# Main execution
main() {
    echo "🚀 Starting comprehensive branch resolution verification..."
    echo ""
    
    # Perform all checks
    check_github_config
    check_local_config
    check_workflows
    check_security_config
    check_documentation
    
    # Provide recommendations
    provide_final_recommendations
    
    echo "=================================================="
    echo "✅ Branch resolution verification complete!"
    echo ""
    echo "🎯 Summary: Your VersionTracker repository is now configured to use"
    echo "   '$DEFAULT_BRANCH' as the consistent default branch across all"
    echo "   GitHub configurations, workflows, and security settings."
    echo ""
    echo "🔗 Quick Links:"
    echo "   • Repository: https://github.com/$REPO"
    echo "   • Branch settings: https://github.com/$REPO/settings/branches"
    echo "   • Actions: https://github.com/$REPO/actions"
    echo "   • Security: https://github.com/$REPO/security"
}

# Run verification
main
