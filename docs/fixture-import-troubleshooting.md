# Fixture Import and Docker Build Troubleshooting

## Overview
This document covers common issues with Frappe fixture imports and Docker build processes in the intralogistics project.

## Fixture Import Issues

### Symptom: Server Scripts import but MODBUS Connection doesn't
**Root Cause:** Fixture file format or missing files in remote repository

**Diagnosis Steps:**
1. Check fixture file exists in container: `docker compose exec backend ls /home/frappe/frappe-bench/apps/epibus/epibus/fixtures/`
2. Verify fixture format - must be array `[{}]` not object `{}`
3. Confirm file exists in remote repository (build pulls from GitHub, not local)

**Solution:**
- Fix fixture format: Change `{"doctype": "..."}` to `[{"doctype": "..."}]`
- Push missing files to remote repository
- Rebuild image to pull latest changes

### Fixture Format Requirements
```json
// ❌ Wrong (object format)
{
  "doctype": "Modbus Connection",
  "device_name": "Example"
}

// ✅ Correct (array format)
[
  {
    "doctype": "Modbus Connection", 
    "device_name": "Example"
  }
]
```

## Docker Build Issues

### Symptom: Changes not appearing in builds despite push to remote
**Root Cause:** Docker build cache persists git clone operations

**Solutions (in order of preference):**
1. `docker builder prune --all -f` - Clear build cache
2. `docker rmi -f frappe-epibus:latest` - Remove old image completely
3. Use `--no-cache` flag: `./development/build-epibus-image.sh --no-cache`

### Build Time Expectations
- **Cached builds:** 2-5 minutes
- **Fresh builds:** 10-15 minutes  
- **No-cache builds:** 15-25 minutes
- Spindumps and Docker Desktop stress are normal during intensive builds

### Repository Structure
- Build pulls from `https://github.com/appliedrelevance/epibus` 
- Local changes in `/epibus/` don't affect builds until pushed to remote
- Ensure nested `/epibus/` git remote points to epibus repo: `git remote set-url origin https://github.com/appliedrelevance/epibus.git`

## Debugging Workflow

1. **Verify fixture exists locally:** Check file in `/epibus/epibus/fixtures/`
2. **Check fixture format:** Ensure array format `[{}]`
3. **Push to remote:** Commit and push changes to epibus repository  
4. **Clear build cache:** `docker builder prune --all -f`
5. **Fresh build:** `./development/build-epibus-image.sh --no-cache`
6. **Deploy and test:** `./deploy.sh lab` and check web interface

## Prevention
- Always test fixture format locally before committing
- Push fixture changes before building
- Use proper git remotes for subdirectories representing separate repos
- Document any new fixture requirements in hooks.py

## Related Files
- `epibus/epibus/hooks.py` - Fixture definitions
- `epibus/epibus/fixtures/` - Fixture data files  
- `development/build-epibus-image.sh` - Custom image build script
- `deploy.sh` - Deployment orchestration