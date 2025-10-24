# Production Environment Configuration

Use this as a reference for production settings.

## Security

### 1. Update Secret Key
In `config.py`, change:
```python
SECRET_KEY = 'your-secret-key-change-this-in-production'
```

Generate a secure key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2. File Permissions
```bash
# Ensure proper ownership
sudo chown -R pi:pi ~/fpl-dashboard

# Secure config file
chmod 600 ~/fpl-dashboard/config.py

# Secure database directory
chmod 700 ~/fpl-dashboard/data
```

### 3. Firewall Configuration
```bash
# Enable UFW
sudo ufw enable

# Allow SSH (if using)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

## Performance Optimization

### 1. Gunicorn Workers
In `systemd/vantix.service`:
- **2GB RAM**: Use 2 workers
- **4GB RAM**: Use 3-4 workers
- **8GB RAM**: Use 4 workers

### 2. Database Optimization
```bash
# Run VACUUM periodically to optimize database
sqlite3 data/fpl_dashboard.db "VACUUM;"

# Create a cron job for weekly optimization
crontab -e

# Add this line (runs every Sunday at 2 AM):
0 2 * * 0 cd ~/fpl-dashboard && sqlite3 data/fpl_dashboard.db "VACUUM;"
```

### 3. Log Rotation
Create `/etc/logrotate.d/vantix`:
```
/home/pi/fpl-dashboard/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0644 pi pi
}
```

## Monitoring

### 1. System Resources
```bash
# Monitor CPU and memory
htop

# Monitor disk space
df -h

# Monitor specific process
ps aux | grep gunicorn
```

### 2. Application Health
```bash
# Check if service is running
sudo systemctl status vantix

# Check recent logs
sudo journalctl -u vantix -n 50

# Monitor logs in real-time
tail -f ~/fpl-dashboard/logs/error.log
```

### 3. Setup Monitoring Script
Create `~/monitor_vantix.sh`:
```bash
#!/bin/bash
if ! systemctl is-active --quiet vantix; then
    echo "Vantix is down! Restarting..."
    sudo systemctl restart vantix
    echo "Vantix restarted at $(date)" >> ~/vantix_restarts.log
fi
```

Add to crontab to run every 5 minutes:
```
*/5 * * * * ~/monitor_vantix.sh
```

## Backup Strategy

### 1. Database Backup Script
Create `~/backup_vantix.sh`:
```bash
#!/bin/bash
BACKUP_DIR=~/vantix_backups
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp ~/fpl-dashboard/data/fpl_dashboard.db $BACKUP_DIR/fpl_dashboard_$DATE.db

# Keep only last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete

echo "Backup completed: fpl_dashboard_$DATE.db"
```

Make executable and add to crontab:
```bash
chmod +x ~/backup_vantix.sh

# Add to crontab (daily at 1 AM)
0 1 * * * ~/backup_vantix.sh
```

### 2. Configuration Backup
```bash
# Backup config file
cp ~/fpl-dashboard/config.py ~/fpl-dashboard/config.py.backup
```

## SSL/TLS Configuration

### 1. Let's Encrypt Auto-Renewal
Certbot automatically sets up renewal. Test it:
```bash
sudo certbot renew --dry-run
```

### 2. SSL Security Headers
Already included in `nginx/vantix.conf`:
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Strict-Transport-Security (HTTPS only)

### 3. SSL Labs Test
After SSL setup, test your configuration:
https://www.ssllabs.com/ssltest/

## Nginx Optimization

### 1. Enable Gzip Compression
Add to nginx config in the `http` block:
```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/css text/javascript application/javascript application/json;
```

### 2. Browser Caching
Already configured in `nginx/vantix.conf` for static files (30 days).

### 3. Rate Limiting
Add to nginx config to prevent abuse:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20;
    # ... rest of config
}
```

## Updates and Maintenance

### 1. System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Reboot if kernel updated
sudo reboot
```

### 2. Python Dependencies
```bash
cd ~/fpl-dashboard
source venv/bin/activate
pip list --outdated
pip install --upgrade <package-name>
```

### 3. Application Updates
```bash
cd ~/fpl-dashboard
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart vantix
```

## Troubleshooting Production Issues

### High Memory Usage
```bash
# Check memory usage
free -h

# Reduce Gunicorn workers in vantix.service
sudo systemctl daemon-reload
sudo systemctl restart vantix
```

### Slow Response Times
```bash
# Check database size
du -h data/fpl_dashboard.db

# Optimize database
sqlite3 data/fpl_dashboard.db "VACUUM; ANALYZE;"
```

### Service Crashes
```bash
# Check crash logs
sudo journalctl -u vantix --since "1 hour ago"

# Increase restart limits in vantix.service if needed
```

## Production Checklist

Before going live:

- [ ] Secret key updated in config.py
- [ ] File permissions secured
- [ ] Firewall configured
- [ ] SSL certificate installed
- [ ] Backup script configured
- [ ] Log rotation configured
- [ ] Monitoring script active
- [ ] All services start on boot
- [ ] Domain DNS correctly configured
- [ ] Test all features work in production
- [ ] Test from multiple devices
- [ ] Set up error notifications (optional)

## Contact & Support

For production issues:
1. Check logs first: `tail -f ~/fpl-dashboard/logs/error.log`
2. Review systemd logs: `sudo journalctl -u vantix -n 100`
3. Check Nginx logs: `sudo tail -f /var/log/nginx/vantix_error.log`
4. Restart services: `sudo systemctl restart vantix nginx`

---

**Remember**: Always test changes in development before applying to production!
