# 🚀 IntralogisticsAI Production Deployment Guide

## Pre-Production Checklist ✅

### System Requirements
- **Hardware**: 8GB+ RAM, 4+ CPU cores, 50GB+ storage
- **OS**: Linux (Ubuntu 20.04+), macOS, Windows 11 with WSL2
- **Network**: Static IP, domain name, SSL certificate capability
- **Ports**: 80, 443, 502 (MODBUS), 7654 (PLC Bridge) open

### Software Requirements
```bash
# Install Docker Engine (not Docker Desktop for production)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose V2
sudo apt update && sudo apt install docker-compose-plugin
```

## 🌐 Production Deployment Options

### Option 1: Web Deployment (Recommended)
```bash
# 1. Clone repository
git clone https://github.com/appliedrelevance/intralogisticsai
cd intralogisticsai

# 2. Configure production environment
cp example.env .env
nano .env  # Set production values

# 3. Deploy with your domain
./deploy.sh web yourdomain.com

# 4. Complete one-time setup wizard (2 minutes)
# Access https://yourdomain.com and complete setup
```

**Access Points:**
- Main ERP: `https://yourdomain.com`
- OpenPLC: `https://openplc.yourdomain.com`
- Dashboard: `https://dashboard.yourdomain.com`

### Option 2: Lab Environment
```bash
# Perfect for training environments and demos
./deploy.sh lab
```

**Access Points:**
- Main ERP: `http://intralogistics.lab`  
- OpenPLC: `http://openplc.intralogistics.lab`
- Dashboard: `http://dashboard.intralogistics.lab`

## ⚙️ Production Environment Configuration

### Required .env Variables
```bash
# Production essentials
ERPNEXT_VERSION=v15.64.1
DB_PASSWORD=<secure-random-password>
WEB_DOMAIN=yourdomain.com
LETSENCRYPT_EMAIL=admin@yourdomain.com

# Security settings
FRAPPE_API_KEY=<secure-random-key>
FRAPPE_API_SECRET=<secure-random-secret>

# Optional optimizations
CLIENT_MAX_BODY_SIZE=100m
PROXY_READ_TIMEOUT=300s
```

### DNS Configuration
```bash
# A Records required:
yourdomain.com          → YOUR_SERVER_IP
openplc.yourdomain.com  → YOUR_SERVER_IP  
dashboard.yourdomain.com → YOUR_SERVER_IP
```

## 🔒 Security Hardening

### 1. SSL/HTTPS Setup (Automatic)
The deployment automatically provisions SSL certificates via Let's Encrypt.

### 2. Database Security
```bash
# Change default database password
docker compose exec db mysql -u root -p
ALTER USER 'root'@'%' IDENTIFIED BY 'new_secure_password';
FLUSH PRIVILEGES;
```

### 3. Application Security
- Change default admin password immediately
- Enable two-factor authentication
- Configure user roles and permissions
- Regular security updates

### 4. Network Security
```bash
# Configure firewall (Ubuntu/Debian)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS  
sudo ufw allow 502/tcp     # MODBUS TCP
sudo ufw enable
```

## 📊 Production Monitoring

### Health Check Endpoints
```bash
# Application health
curl https://yourdomain.com/api/method/ping

# OpenPLC health  
curl https://openplc.yourdomain.com/

# Container health
docker compose ps
```

### Log Monitoring
```bash
# Application logs
docker compose logs -f backend

# OpenPLC logs
docker compose logs -f openplc  

# PLC Bridge logs
docker compose logs -f plc-bridge

# Nginx logs
docker compose logs -f frontend
```

### Performance Monitoring
```bash
# Resource usage
docker stats

# Database performance
docker compose exec backend bench --site yourdomain.com mariadb -e "SHOW PROCESSLIST;"
```

## 🔧 Production Operations

### Backup Strategy
```bash
# Automated daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"

# Database backup
docker compose exec backend bench --site yourdomain.com backup \
  --with-files --backup-path $BACKUP_DIR/db_$DATE

# Files backup  
docker run --rm -v intralogisticsai_sites:/data \
  -v $BACKUP_DIR:/backup alpine tar czf /backup/files_$DATE.tar.gz /data

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

### Updates and Maintenance
```bash
# Update to latest version
git pull origin main
docker compose pull
./deploy.sh web yourdomain.com --rebuild

# Database migrations
docker compose exec backend bench --site yourdomain.com migrate

# Clear cache
docker compose exec backend bench --site yourdomain.com clear-cache
```

### Scaling Considerations
```bash
# Horizontal scaling (multiple backends)
cp overrides/compose.multi-bench.yaml overrides/compose.production.yaml
docker compose -f compose.yaml -f overrides/compose.production.yaml up -d

# Database replication for high availability
# See docs/deployment/ha-setup.md (TODO: create this)
```

## 🚨 Troubleshooting Production Issues

### Common Issues

#### 1. Site Not Loading
```bash
# Check container status
docker compose ps

# Check logs
docker compose logs frontend
docker compose logs backend

# Restart services
docker compose restart frontend backend
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
docker compose exec backend bench --site yourdomain.com console
# In console: frappe.db.sql("SELECT 1")

# Reset database connection
docker compose restart db
docker compose restart backend
```

#### 3. SSL Certificate Issues
```bash
# Force certificate renewal
docker compose exec proxy traefik acme renew

# Check certificate status  
curl -I https://yourdomain.com
```

#### 4. MODBUS Communication Issues
```bash
# Test MODBUS connectivity
nc -z localhost 502

# Check OpenPLC runtime
docker compose logs openplc

# Restart PLC services
docker compose restart openplc plc-bridge
```

### Performance Issues
```bash
# Database optimization
docker compose exec backend bench --site yourdomain.com optimize-database

# Clear sessions
docker compose exec backend bench --site yourdomain.com clear-sessions

# Rebuild search index
docker compose exec backend bench --site yourdomain.com build-search-index
```

## 📈 Production Best Practices

### 1. Resource Allocation
- **Minimum**: 4 CPU cores, 8GB RAM, 50GB storage
- **Recommended**: 8 CPU cores, 16GB RAM, 100GB SSD storage
- **High Load**: 16+ CPU cores, 32GB+ RAM, NVMe storage

### 2. Database Optimization
```sql
-- MySQL/MariaDB production tuning
SET GLOBAL innodb_buffer_pool_size = 4G;  -- 50-80% of RAM
SET GLOBAL max_connections = 500;
SET GLOBAL query_cache_size = 256M;
```

### 3. Backup Schedule
- **Database**: Every 6 hours
- **Files**: Daily
- **Full System**: Weekly
- **Test Restores**: Monthly

### 4. Update Schedule
- **Security Updates**: Immediate
- **Minor Updates**: Monthly
- **Major Updates**: Quarterly (with testing)

## 🎯 Go-Live Checklist

### Pre-Launch (1 week before)
- [ ] Complete setup wizard with production data
- [ ] Configure all user accounts and permissions
- [ ] Test all integrations (MODBUS, APIs)
- [ ] Load test with expected user volume
- [ ] Verify backup and restore procedures
- [ ] Document custom configurations

### Launch Day
- [ ] Final data migration
- [ ] DNS cutover to production
- [ ] SSL certificate validation
- [ ] End-to-end functionality test
- [ ] User acceptance testing
- [ ] Monitor logs for first 4 hours

### Post-Launch (first week)
- [ ] Daily health checks
- [ ] Performance monitoring
- [ ] User feedback collection
- [ ] Documentation updates
- [ ] Team training completion

## 📞 Production Support

### Monitoring Alerts
Set up alerts for:
- Container health failures
- High memory/CPU usage (>80%)
- Database connection failures  
- SSL certificate expiration
- Disk space warnings (<10% free)

### Escalation Path
1. **Level 1**: Restart affected services
2. **Level 2**: Check logs and apply standard fixes
3. **Level 3**: Contact development team with logs

---

**🎉 Your IntralogisticsAI platform is production-ready!**

For additional support, see the [troubleshooting guide](docs/troubleshooting/README.md) or create an issue on GitHub.