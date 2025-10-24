# Vantix Deployment Checklist

Use this checklist to ensure smooth deployment on your Raspberry Pi.

## Pre-Deployment

- [ ] Raspberry Pi 4 is set up and accessible via SSH
- [ ] Domain name is registered and DNS points to Pi's IP address
- [ ] Python 3.8+ is installed (`python3 --version`)
- [ ] Git is installed (`git --version`)
- [ ] You have your FPL Team ID and Classic League ID

## Initial Setup

- [ ] Clone repository to `~/fpl-dashboard`
- [ ] Run `./setup.sh` to configure environment
- [ ] Update `config.py` with your FPL IDs
- [ ] Run initial data collection (`python data/fpl_api.py`)
- [ ] Test application locally (`python app.py`)
- [ ] Verify dashboard loads at http://localhost:5000

## Nginx Configuration

- [ ] Install Nginx: `sudo apt install nginx`
- [ ] Copy config: `sudo cp nginx/vantix.conf /etc/nginx/sites-available/vantix`
- [ ] Edit config: `sudo nano /etc/nginx/sites-available/vantix`
- [ ] Update domain name in config file
- [ ] Enable site: `sudo ln -s /etc/nginx/sites-available/vantix /etc/nginx/sites-enabled/`
- [ ] Test config: `sudo nginx -t`
- [ ] Restart Nginx: `sudo systemctl restart nginx`
- [ ] Verify HTTP access via domain name

## Systemd Service

- [ ] Copy service: `sudo cp systemd/vantix.service /etc/systemd/system/`
- [ ] Edit if needed: `sudo nano /etc/systemd/system/vantix.service`
- [ ] Update paths if not using `/home/pi/fpl-dashboard`
- [ ] Reload systemd: `sudo systemctl daemon-reload`
- [ ] Start service: `sudo systemctl start vantix`
- [ ] Check status: `sudo systemctl status vantix`
- [ ] Enable auto-start: `sudo systemctl enable vantix`
- [ ] Test application via domain name

## SSL/HTTPS Setup

- [ ] Install certbot: `sudo apt install certbot python3-certbot-nginx`
- [ ] Run certbot: `sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com`
- [ ] Follow prompts to complete SSL setup
- [ ] Test HTTPS access: https://yourdomain.com
- [ ] Verify auto-renewal: `sudo certbot renew --dry-run`

## Post-Deployment

- [ ] Test all dashboard features:
  - [ ] Stats cards display correctly
  - [ ] Cumulative points chart loads
  - [ ] League position chart loads
  - [ ] Team filtering works
  - [ ] Recent transfers display
  - [ ] Refresh button works
- [ ] Test on multiple devices:
  - [ ] Desktop browser
  - [ ] Tablet
  - [ ] Mobile phone
- [ ] Verify scheduled updates work (check after next gameweek)
- [ ] Set up monitoring (optional)
- [ ] Configure backups (optional)

## Optional Enhancements

- [ ] Configure firewall: `sudo ufw allow 80,443/tcp`
- [ ] Set up log rotation
- [ ] Configure monitoring (e.g., uptime monitoring)
- [ ] Add analytics (optional)
- [ ] Create database backup script

## Troubleshooting Checks

If something doesn't work:

- [ ] Check systemd service: `sudo systemctl status vantix`
- [ ] View application logs: `tail -f ~/fpl-dashboard/logs/error.log`
- [ ] View Nginx logs: `sudo tail -f /var/log/nginx/vantix_error.log`
- [ ] Test Gunicorn directly: `cd ~/fpl-dashboard && source venv/bin/activate && gunicorn --bind 127.0.0.1:8000 wsgi:app`
- [ ] Verify database exists: `ls -lh ~/fpl-dashboard/data/fpl_dashboard.db`
- [ ] Check FPL API access: `curl https://fantasy.premierleague.com/api/bootstrap-static/ | head`

## Maintenance Schedule

Weekly:
- [ ] Check application logs for errors
- [ ] Verify data is updating after gameweeks

Monthly:
- [ ] Review disk space usage
- [ ] Check for application updates
- [ ] Verify SSL certificate renewal

## Notes

Additional setup notes:

_______________________________________________________________

_______________________________________________________________

_______________________________________________________________

## Completion

Deployment completed on: ____________________

Deployed by: ____________________

Domain: ____________________

Happy FPL tracking! 🏆
