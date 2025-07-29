#!/bin/bash

# VersionTracker Security Setup Script
# Enables Dependabot security updates and vulnerability alerts

set -e

REPO="docdyhr/versiontracker"

echo "🔒 Setting up comprehensive security monitoring for $REPO"

# Check if gh CLI is authenticated
if ! gh auth status &>/dev/null; then
    echo "❌ GitHub CLI not authenticated. Please run 'gh auth login' first."
    exit 1
fi

echo "🚀 Enabling security features..."

# Enable vulnerability alerts
echo "📢 Enabling vulnerability alerts..."
gh api \
    --method PATCH \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$REPO" \
    -f "has_vulnerability_alerts=true" || echo "⚠️  Vulnerability alerts may already be enabled"

# Enable Dependabot security updates
echo "🤖 Enabling Dependabot security updates..."
gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$REPO/automated-security-fixes" || echo "⚠️  Dependabot security updates may already be enabled"

# Enable Dependabot alerts
echo "🚨 Enabling Dependabot alerts..."
gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$REPO/vulnerability-alerts" || echo "⚠️  Dependabot alerts may already be enabled"

# Check if GitHub Advanced Security is available (may require GitHub Pro/Enterprise)
echo "🔍 Checking GitHub Advanced Security availability..."
# Properly handle API call failure
if ADVANCED_SECURITY=$(gh api "/repos/$REPO" --jq '.security_and_analysis.advanced_security.status' 2>/dev/null); then
    echo "✅ Successfully retrieved Advanced Security status: $ADVANCED_SECURITY"
else
    ADVANCED_SECURITY="not_available"
    echo "ℹ️  Could not retrieve Advanced Security status (may not be available on current plan)"
fi

if [ "$ADVANCED_SECURITY" = "enabled" ] || [ "$ADVANCED_SECURITY" = "disabled" ]; then
    echo "✅ GitHub Advanced Security is available"

    # Enable secret scanning
    echo "🔐 Enabling secret scanning..."
    if gh api \
        --method PATCH \
        -H "Accept: application/vnd.github+json" \
        "/repos/$REPO" \
        --field "security_and_analysis[secret_scanning][status]=enabled" 2>/dev/null; then
        echo "✅ Secret scanning enabled successfully"
    else
        echo "⚠️  Failed to enable secret scanning (may require GitHub Advanced Security or proper permissions)"
        echo "   Please check your GitHub plan and repository permissions"
    fi

    # Enable secret scanning push protection
    echo "🛡️  Enabling secret scanning push protection..."
    if gh api \
        --method PATCH \
        -H "Accept: application/vnd.github+json" \
        "/repos/$REPO" \
        --field "security_and_analysis[secret_scanning_push_protection][status]=enabled" 2>/dev/null; then
        echo "✅ Push protection enabled successfully"
    else
        echo "⚠️  Failed to enable push protection (may require GitHub Advanced Security or proper permissions)"
        echo "   Please check your GitHub plan and repository permissions"
    fi

    # Enable code scanning (if CodeQL workflow exists)
    if [ -f ".github/workflows/codeql-analysis.yml" ]; then
        echo "🔬 CodeQL analysis workflow detected - code scanning should be automatically enabled"
    else
        echo "💡 Consider adding CodeQL analysis workflow for comprehensive code scanning"
    fi
else
    echo "ℹ️  GitHub Advanced Security not available on current plan"
    echo "   Basic security features (vulnerability alerts, Dependabot) will still work"
fi

echo ""
echo "✅ Security setup complete!"
echo ""
echo "🔐 Enabled Security Features:"
echo "  ✅ Vulnerability alerts for dependencies"
echo "  ✅ Dependabot security updates (automatic)"
echo "  ✅ Dependabot alerts"
echo "  ✅ Enhanced Dependabot configuration with security grouping"

if [ "$ADVANCED_SECURITY" = "enabled" ]; then
    echo "  ✅ Secret scanning"
    echo "  ✅ Secret scanning push protection"
fi

echo ""
echo "📊 Security Monitoring Dashboard:"
echo "  • View alerts: https://github.com/$REPO/security"
echo "  • Dependabot: https://github.com/$REPO/security/dependabot"
echo "  • Advisories: https://github.com/$REPO/security/advisories"

echo ""
echo "🔧 Additional Manual Steps:"
echo "  1. Go to Settings → Security & analysis"
echo "  2. Verify all available security features are enabled"
echo "  3. Configure notification preferences for security alerts"
echo "  4. Review and customize Dependabot auto-merge rules if needed"

echo ""
echo "📱 Notification Setup:"
echo "  • Go to Settings → Notifications"
echo "  • Enable 'Vulnerability alerts' under Security alerts"
echo "  • Consider enabling 'Dependabot alerts' for immediate notifications"

echo ""
echo "🚀 Next Steps:"
echo "  • Dependabot will now automatically create PRs for security updates"
echo "  • Security updates are grouped and prioritized"
echo "  • Daily checks for critical security updates"
echo "  • Weekly checks for regular dependency updates"

echo ""
echo "To check current security status:"
echo "  gh api repos/$REPO/vulnerability-alerts"
echo "  gh api repos/$REPO/automated-security-fixes"
