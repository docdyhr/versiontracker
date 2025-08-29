# 🔐 PyPI Trusted Publisher Setup Guide

## ❗ CRITICAL: This must be completed by repository owner to enable releases

### 🎯 **Current Status**
- ❌ **PyPI trusted publisher NOT configured** 
- ❌ **All releases failing at publishing step**
- ✅ **Workflow configuration is correct**

---

## 📋 **Required Configuration**

### **Step 1: Access PyPI Package Settings**

Visit: https://pypi.org/manage/project/homebrew-versiontracker/settings/publishing/

### **Step 2: Add Trusted Publisher**

Click **"Add a new trusted publisher"** and enter these **EXACT** values:

```yaml
Repository owner: docdyhr
Repository name: versiontracker
Workflow name: release.yml
Environment name: pypi
```

### **Step 3: Verify Configuration**

After saving, you should see:
```
✅ Trusted publisher configured for:
   Repository: docdyhr/versiontracker
   Workflow: .github/workflows/release.yml  
   Environment: pypi
```

---

## 🧪 **Testing the Configuration**

Once configured, test with these commands:

```bash
# Create and push a test release
git tag v0.8.0-test
git push origin v0.8.0-test

# Or trigger manual release
gh workflow run release.yml -f version=v0.8.0-test -f prerelease=true
```

---

## 🔍 **Verification Checklist**

- [ ] PyPI trusted publisher configured with exact values above
- [ ] Repository owner has necessary PyPI permissions  
- [ ] Test release succeeds without "invalid-publisher" error
- [ ] Package appears on PyPI: https://pypi.org/project/homebrew-versiontracker/

---

## 🆘 **Troubleshooting**

### Error: "invalid-publisher" 
- **Cause**: Configuration mismatch or not saved
- **Fix**: Double-check all values match exactly

### Error: "insufficient permissions"
- **Cause**: Account lacks PyPI project permissions
- **Fix**: Contact current package maintainer

### Workflow still fails
- **Cause**: GitHub environment not configured
- **Fix**: Verify `pypi` environment exists in repository settings

---

## 📞 **Support**

If issues persist:
1. Check https://docs.pypi.org/trusted-publishers/troubleshooting/
2. Verify GitHub repository settings > Environments > pypi exists
3. Ensure all workflow YAML syntax is correct

**Status**: ⏳ **Awaiting manual PyPI configuration**