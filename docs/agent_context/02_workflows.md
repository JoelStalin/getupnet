# Development Workflows
> Guide for developing, testing, and deploying changes.

## Environment Setup
**Docker is standard.**
- **Start**: `docker compose up -d`
- **Rebuild**: `docker compose build` (needed when adding python dependencies).
- **Logs**: `docker compose logs -f odoo`

## Testing Strategy
1. **Unit Tests**:
    - Location: `tests/`
    - Run: `docker compose exec odoo pytest /mnt/tests`
2. **Browser Automation (Selenium)**:
    - Location: `tests/isp_selenium/`
    - Setup: Requires running `selenium` container.
    - Run: `pytest tests/isp_selenium`

## Common Tasks

### Adding a New Module
1. Create folder in `addons/`.
2. Add `__manifest__.py`.
3. Add to `docker-compose.yml` volumes if outside `addons/`. (Currently all in `addons/`).
4. Install via UI or CLI.

### Debugging MikroTik Integration
- **Dry Run**: Set `isp_mikrotik.dry_run = 1` in System Parameters to simulate API calls without hardware.
- **Logs**: Check `isp.provisioning_job` records for API responses and errors.

### Database Management
- **Reset**: `docker compose down -v` (destroys DB volume).
- **Backup**: Use Odoo's `/web/database/manager` or `pg_dump` from db container.

## Deployment Checklist
- [ ] Set `isp_mikrotik.dry_run = 0`
- [ ] Change admin password.
- [ ] Configure `isp_core.mac_onboarding_token` (secure random string).
- [ ] Set `ISP_HOME_TOKEN` env var for call-home feature.
- [ ] Configure outgoing mail server (SMTP).

## Management Tools

### AWS CLI & DNS Updates
To enable dynamic DNS updates for `isp.getupsoft.com.do`:

1. **Install AWS CLI**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install awscli jq -y
   
   # Verify
   aws --version
   ```

2. **Configure Credentials**:
   Run `aws configure` and provide Access Key/Secret Key with Route 53 permissions.

3. **Setup DNS Script**:
   - Edit `tools/aws_route53_update.sh`.
   - Set `HOSTED_ZONE_ID` (from AWS Console).
   - Ensure script is executable: `chmod +x tools/aws_route53_update.sh`.
   - Add to crontab (e.g., every 5 mins):
     `*/5 * * * * /path/to/getupnet/tools/aws_route53_update.sh`

### Port Validation
The script checks if ports **80, 443, and 8069** are matching local listeners before updating DNS. Using `ss` or `netstat`.

## Management & Automation Tools

### Windows Management Script (`tools/manage.ps1`)
Unified PowerShell script for common operations.
```powershell
.\tools\manage.ps1 up           # Start containers
.\tools\manage.ps1 shell        # Access Odoo container (SSH-like)
.\tools\manage.ps1 logs         # View logs
.\tools\manage.ps1 aws <cmd>    # Run AWS CLI inside container. Ex: aws s3 ls
```

### Automation Scripts

1. **Selenium Wrapper**:
   - Run via `manage.ps1 selenium` or `python tools/run_selenium.py`.
   - Executes tests in `tests/isp_selenium`.
   - Sets up `ISP_E2E=1` automatically.

2. **MikroTik Manager**:
   - CLI for router operations.
   - Run via `manage.ps1 mikrotik <cmd>` or directly in container.
   - Commands: `list`, `jobs`, `run` (triggers provisioning cron).

3. **Endpoint Tester**:
   - Verifies portal availability.
   - Run via `manage.ps1 endpoints` or `python tools/test_endpoints.py`.
