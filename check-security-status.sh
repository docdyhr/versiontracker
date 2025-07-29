#!/bin/bash

# Security Status Verification Script
# Checks the current security configuration status

set -e

REPO="docdyhr/versiontracker"

echo "🔍 Checking security status for $REPO"
echo ""

# Check vulnerability alerts
echo "📢 Vulnerability Alerts Status:"
if gh api repos/$REPO/vulnerability-alerts &>/dev/null; then
    echo "  ✅ Enabled"
else
    echo "  ❌ Disabled or error"
fi

# Check automated security fixes
echo "🤖 Automated Security Fixes Status:"
if gh api repos/$REPO/automated-security-fixes &>/dev/null; then
    echo "  ✅ Enabled"
else
    echo "  ❌ Disabled or error"
fi

# Check Dependabot configuration
echo "📋 Dependabot Configuration:"
if [ -f ".github/dependabot.yml" ]; then
    echo "  ✅ Configuration file exists"
    echo "  📊 Update schedules:"
    grep -A1 "interval:" .github/dependabot.yml | sed 's/^/    /'
else
    echo "  ❌ No configuration file found"
fi

# Check security workflows
echo "🔬 Security Workflows:"
if [ -f ".github/workflows/security-audit.yml" ]; then
    echo "  ✅ Security audit workflow configured"
else
    echo "  ❌ No security audit workflow"
fi

if [ -f ".github/workflows/security.yml" ]; then
    echo "  ✅ Main security workflow exists"
else
    echo "  ⚠️  Main security workflow not found"
fi

# Check security policy
echo "📋 Security Policy:"
if [ -f "SECURITY.md" ]; then
    echo "  ✅ Security policy exists"
else
    echo "  ❌ No security policy found"
fi

# Check current vulnerabilities
echo ""
echo "🚨 Current Security Status:"
echo "  Visit: https://github.com/$REPO/security/dependabot"
echo "  Visit: https://github.com/$REPO/security"

# Check if there are any existing security alerts
echo ""
echo "💡 Next Steps:"
echo "  1. Monitor the Security tab for any existing alerts"
echo "  2. Review Dependabot PRs when they appear"
echo "  3. Configure notification preferences in GitHub settings"
echo "  4. Run local security scans: 'safety check' and 'pip-audit'"

echo ""
echo "✅ Security monitoring setup verification complete!"
