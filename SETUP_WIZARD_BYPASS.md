# 🧙‍♂️ ERPNext Setup Wizard Bypass Guide

## Problem
ERPNext shows a setup wizard on first login that requires manual completion. This is fine for production but inconvenient for training labs where you want immediate access.

## Solution Options

### Option 1: One-Time Manual Setup (Recommended)
**Time**: 2 minutes per deployment
**Effort**: Low
**Reliability**: 100%

1. Deploy the system normally:
   ```bash
   ./deploy.sh lab  # or web, with-plc, etc.
   ```

2. Access the web interface and login:
   - URL: `http://intralogistics.lab` (or your domain)
   - Username: `Administrator`
   - Password: `admin`

3. Complete the setup wizard with these values:
   - **Language**: English  
   - **Country**: United States
   - **Timezone**: America/New_York
   - **Currency**: USD
   - **Company Name**: Roots Intralogistics
   - **Company Abbreviation**: RL
   - **Email**: admin@rootseducation.co
   - **First Name**: Administrator
   - **Last Name**: User

4. Click "Complete Setup" - done!

### Option 2: Database Template (For Repeated Deployments)
**Time**: 10 minutes setup, 30 seconds per deployment
**Effort**: Medium
**Reliability**: 100%

#### Create Template (One Time)
```bash
# 1. Complete Option 1 above first

# 2. Create database backup
docker compose exec backend bench --site intralogistics.lab backup --with-files

# 3. Copy the backup to your template directory
docker compose cp backend:/home/frappe/frappe-bench/sites/intralogistics.lab/private/backups/ ./templates/

# 4. Rename the backup files
mv templates/backup_files.tar ./templates/production-template-files.tar
mv templates/database.sql.gz ./templates/production-template-db.sql.gz
```

#### Use Template (Each Deployment)
```bash
# 1. Deploy normally but skip the wizard
./deploy.sh lab

# 2. Restore from template
docker compose exec backend bench --site intralogistics.lab restore \
  /home/frappe/frappe-bench/templates/production-template-db.sql.gz \
  --with-private-files /home/frappe/frappe-bench/templates/production-template-files.tar

# 3. Ready to use - no wizard!
```

### Option 3: Docker Image with Pre-completed Setup
**Time**: 30 minutes setup, instant deployments
**Effort**: High
**Reliability**: 95%

#### Build Custom Image (One Time)
```bash
# 1. Complete setup wizard manually in a container
./deploy.sh lab
# Complete wizard via web interface

# 2. Commit the configured container
docker commit intralogisticsai-backend-1 frappe-epibus:configured

# 3. Update environment to use configured image  
export CUSTOM_IMAGE=frappe-epibus
export CUSTOM_TAG=configured
```

#### Deploy Configured Image
```bash
# Use the pre-configured image
CUSTOM_IMAGE=frappe-epibus CUSTOM_TAG=configured ./deploy.sh lab
```

## Recommended Approach by Use Case

### Training Labs (Multiple Workstations)
**Use Option 2 (Database Template)**
- Create template once per semester
- 30-second deployment per workstation
- Consistent configuration across all stations

### Production Deployment
**Use Option 1 (Manual Setup)**
- Only happens once
- Allows customization for specific environment
- Most reliable for production systems

### Demo/Development
**Use Option 1 (Manual Setup)**
- Quick and simple
- No additional complexity
- Easy to customize per demo

## Automation Attempts (Historical)

We attempted to automate the setup wizard completion but encountered these technical challenges with ERPNext v15:

1. **Logging System Dependencies**: ERPNext requires complex directory structures and logging initialization
2. **Frappe Context Issues**: Setup functions need proper Frappe application context
3. **Database Connection Complexity**: Multiple connection layers with specific initialization order

**Result**: Manual completion is actually faster and more reliable than automation attempts.

## Quick Reference

### Setup Wizard Values
```yaml
Language: English (en)
Country: United States  
Timezone: America/New_York
Currency: USD
Company Name: Roots Intralogistics
Company Abbreviation: RL
Email: admin@rootseducation.co
First Name: Administrator
Last Name: User
Chart of Accounts: Standard
Industry: Manufacturing
```

### Post-Setup Verification
```bash
# Test that setup completed successfully
curl http://intralogistics.lab/api/method/ping

# Check company creation
docker compose exec backend bench --site intralogistics.lab console
# In console: frappe.get_doc("Company", "Roots Intralogistics").company_name
```

---

**💡 Pro Tip**: The 2-minute manual setup is actually faster than troubleshooting automation issues and provides a good opportunity to verify the system is working correctly before handing it off to users.