# Quick Fix: PostgreSQL Connection for Azure Web App

_Last applied: 2026-02-12_

## Objective

Restore connectivity between `app-gen360-api` (Azure App Service) and the PostgreSQL VM at `20.226.39.175` so the `/admin/register` endpoint no longer returns HTTP 500.

---

## Steps Performed

1. **Reset VM Credentials**
   - Command run locally:
     ```powershell
     az vm user update `
       --resource-group DemoGoverno `
       --name postgresql-vm `
       --username linuxuser `
       --password "40-Sloth+iny"
     ```
   - Purpose: regain SSH access to configure PostgreSQL and firewall rules.

2. **Configure PostgreSQL to Allow Remote Connections**
   - Edited `/etc/postgresql/*/main/postgresql.conf` to ensure
     ```
     listen_addresses = '*'
     ```
   - Updated `/etc/postgresql/*/main/pg_hba.conf` with Azure outbound IPs (from `setup/check_database_status.ps1`) or with the temporary rule:
     ```
     host    normas    linuxuser    0.0.0.0/0    md5
     ```
   - Restarted PostgreSQL:
     ```bash
     sudo systemctl restart postgresql
     ```

3. **Open Port 5432 on the VM Firewall**

   ```bash
   sudo ufw allow 5432/tcp
   sudo ufw status
   ```

   Ensures the App Service can reach PostgreSQL.

4. **Verify Database Connectivity**
   - From the local machine:
     ```powershell
     curl https://app-gen360-api.azurewebsites.net/health/db
     ```
   - Expected response:
     ```json
     {"status":"ok","database_connected":true,...}
     ```

---

## Result

- Admin registration flow no longer fails with 500.
- `health/db` endpoint reports `database_connected: true` and lists table status.

---

## Follow-Up

- Replace the wide-open `0.0.0.0/0` rule with the specific outbound IP list from `setup/check_database_status.ps1`.
- Consider migrating to Azure Database for PostgreSQL for managed connectivity.
- Rotate the `linuxuser` password regularly and store it securely.
