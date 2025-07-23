#!/bin/bash

# VersionTracker Workflow Branch Cleanup Script
# Ensures all GitHub Actions workflows use consistent branch naming

set -e

REPO="docdyhr/versiontracker"
DEFAULT_BRANCH="master"

echo "🔧 Cleaning up workflow branch references to use '$DEFAULT_BRANCH'"
echo ""

# Function to update workflow files
update_workflow_files() {
    local files_updated=0
    
    if [[ -d ".github/workflows" ]]; then
        for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
            if [[ -f "$workflow" ]]; then
                local workflow_name
                workflow_name=$(basename "$workflow")
                
                echo "🔍 Checking $workflow_name..."
                
                # Check if file contains both main and master references
                if grep -q "branches.*main" "$workflow" && grep -q "branches.*master" "$workflow"; then
                    echo "   ⚠️  Found both 'main' and 'master' references"
                    
                    # Create backup
                    cp "$workflow" "$workflow.backup"
                    
                    # Remove main branch references, keep master
                    sed -i '' '/branches:.*\[.*main.*master.*\]/s/main, //g' "$workflow"
                    sed -i '' '/branches:.*\[.*master.*main.*\]/s/, main//g' "$workflow"
                    sed -i '' 's/\[main, master\]/[master]/g' "$workflow"
                    sed -i '' 's/\[master, main\]/[master]/g' "$workflow"
                    
                    echo "   ✅ Updated to use only '$DEFAULT_BRANCH'"
                    ((files_updated++))
                    
                elif grep -q "branches.*main" "$workflow" && ! grep -q "branches.*master" "$workflow"; then
                    echo "   ⚠️  Found only 'main' references, updating to '$DEFAULT_BRANCH'"
                    
                    # Create backup
                    cp "$workflow" "$workflow.backup"
                    
                    # Replace main with master
                    sed -i '' 's/branches:.*\[main\]/branches: [master]/g' "$workflow"
                    sed -i '' 's/branches: main/branches: master/g' "$workflow"
                    
                    echo "   ✅ Updated to use '$DEFAULT_BRANCH'"
                    ((files_updated++))
                    
                elif grep -q "branches.*master" "$workflow"; then
                    echo "   ✅ Already uses '$DEFAULT_BRANCH' correctly"
                else
                    echo "   ℹ️  No branch references found (workflow_dispatch or other triggers)"
                fi
            fi
        done
    fi
    
    echo ""
    echo "📊 Summary: Updated $files_updated workflow files"
    
    if [[ $files_updated -gt 0 ]]; then
        echo "💾 Backup files created with .backup extension"
        echo "🗑️  Remove backups with: rm .github/workflows/*.backup"
    fi
}

# Function to validate workflow syntax
validate_workflows() {
    echo "🔍 Validating updated workflow syntax..."
    
    local validation_passed=true
    
    for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
        if [[ -f "$workflow" ]] && [[ "$workflow" != *.backup ]]; then
            local workflow_name
            workflow_name=$(basename "$workflow")
            
            # Basic YAML syntax check
            if python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
                echo "   ✅ $workflow_name: Valid YAML syntax"
            else
                echo "   ❌ $workflow_name: Invalid YAML syntax"
                validation_passed=false
            fi
        fi
    done
    
    if [[ "$validation_passed" == true ]]; then
        echo "✅ All workflows passed validation"
    else
        echo "❌ Some workflows failed validation - check syntax"
        echo "💡 Restore from backup if needed: cp workflow.backup workflow"
    fi
    
    echo ""
}

# Function to show the changes made
show_changes() {
    echo "📋 Changes made to workflow files:"
    echo ""
    
    for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
        if [[ -f "$workflow.backup" ]]; then
            local workflow_name
            workflow_name=$(basename "$workflow")
            
            echo "🔄 $workflow_name:"
            echo "   Before: $(grep -n "branches:" "$workflow.backup" | head -2 | sed 's/^/      /')"
            echo "   After:  $(grep -n "branches:" "$workflow" | head -2 | sed 's/^/      /')"
            echo ""
        fi
    done
}

# Function to update any remaining references in other files
update_other_references() {
    echo "🔍 Checking for branch references in other configuration files..."
    
    # Check README for branch badges or links
    if [[ -f "README.md" ]]; then
        if grep -q "main" README.md; then
            echo "   ⚠️  Found 'main' references in README.md - consider updating manually"
        fi
    fi
    
    # Check contributing guidelines
    if [[ -f "CONTRIBUTING.md" ]]; then
        if grep -q "main" CONTRIBUTING.md; then
            echo "   ⚠️  Found 'main' references in CONTRIBUTING.md - consider updating manually"
        fi
    fi
    
    # Check any documentation
    if [[ -d "docs" ]]; then
        if grep -r "main" docs/ &>/dev/null; then
            echo "   ⚠️  Found 'main' references in docs/ - consider updating manually"
        fi
    fi
    
    echo ""
}

# Main execution
main() {
    echo "🚀 Starting workflow branch cleanup..."
    echo ""
    
    # Update workflow files
    update_workflow_files
    
    # Validate the changes
    validate_workflows
    
    # Show what changed
    show_changes
    
    # Check other files
    update_other_references
    
    echo "✅ Workflow branch cleanup complete!"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Review the changes made to workflow files"
    echo "   2. Test workflows by creating a test PR"
    echo "   3. Remove backup files if everything looks good: rm .github/workflows/*.backup"
    echo "   4. Commit and push the workflow updates"
    echo ""
    echo "🔗 Monitor workflow runs at: https://github.com/$REPO/actions"
}

# Run main function
main
