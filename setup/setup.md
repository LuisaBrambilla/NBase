# Gen360 PostgreSQL Setup Log

## Date: February 12, 2026

## VM Information

- **Name:** postgresql-vm
- **Resource Group:** DemoGoverno
- **Size:** Standard_E2s_v3 (2 vCPUs, 16 GB RAM)
- **OS:** Ubuntu Server 22.04 (Jammy)
- **Location:** brazilsouth
- **Public IP:** 20.226.39.175

## Network Security Group Rules

### SSH Access (Port 22)

```bash
Priority: 1000
Source: * (Any)
Destination Port: 22
Access: Allow
Protocol: TCP
```

### PostgreSQL Access (Port 5432)

```bash
Priority: 1001
Source: * (Any)
Destination Port: 5432
Access: Allow
Protocol: TCP
```

**Status:** ✅ Firewall rules configured correctly

---

## Commands Executed Successfully

### 1. Check VM Details

```powershell
az vm show --resource-group DemoGoverno --name postgresql-vm --query "{Name:name, Size:hardwareProfile.vmSize, OS:storageProfile.imageReference.offer, Location:location}" --output table
```

**Result:** VM running Ubuntu Server 22.04, Standard_E2s_v3

### 2. Get Public IP

```powershell
az vm list-ip-addresses --resource-group DemoGoverno --name postgresql-vm --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" --output tsv
```

**Result:** 20.226.39.175

### 3. List NSG Rules

```powershell
az network nsg rule list -g DemoGoverno --nsg-name postgresql-vm-nsg -o table
```

**Result:** SSH (22) and PostgreSQL (5432) ports are open

### 4. Verify PostgreSQL Version

```powershell
az vm run-command invoke -g DemoGoverno -n postgresql-vm --command-id RunShellScript --scripts "sudo -u postgres psql -c 'SELECT version();'" --query 'value[0].message' -o tsv
```

**Result:** PostgreSQL 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1)

### 5. Create Database

```powershell
az vm run-command invoke -g DemoGoverno -n postgresql-vm --command-id RunShellScript --scripts "sudo -u postgres psql -c 'CREATE DATABASE normas;'" --query 'value[0].message' -o tsv
```

**Result:** ✅ CREATE DATABASE

### 6. Create User

```powershell
az vm run-command invoke -g DemoGoverno -n postgresql-vm --command-id RunShellScript --scripts "sudo -u postgres createuser linuxuser" --query 'value[0].message' -o tsv
```

**Result:** ✅ User created

### 7. Set User Password

```powershell
$pwd = 'r!(hFarm96g5Ayb3INF6'
az vm run-command invoke -g DemoGoverno -n postgresql-vm --command-id RunShellScript --scripts "sudo -u postgres psql -c 'ALTER USER linuxuser WITH PASSWORD '\''$pwd'\'';'" --query 'value[0].message' -o tsv
```

**Result:** ✅ ALTER ROLE

### 8. Grant Privileges

```powershell
az vm run-command invoke -g DemoGoverno -n postgresql-vm --command-id RunShellScript --scripts "sudo -u postgres psql -d normas <<EOF`nGRANT ALL PRIVILEGES ON DATABASE normas TO linuxuser;`nEOF" --query 'value[0].message' -o tsv
```

**Result:** ✅ Privileges granted

### 9. Change Database Owner

```powershell
az vm run-command invoke -g DemoGoverno -n postgresql-vm --command-id RunShellScript --scripts "sudo -u postgres psql <<EOF`nALTER DATABASE normas OWNER TO linuxuser;`nEOF" --query 'value[0].message' -o tsv
```

**Result:** ✅ Owner changed

### 10. Upload Schema File

```powershell
$schema = Get-Content "db\models.sql" -Raw
$encodedSchema = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($schema))
az vm run-command invoke -g DemoGoverno -n postgresql-vm --command-id RunShellScript --scripts "echo '$encodedSchema' | base64 -d > /tmp/models.sql && ls -lh /tmp/models.sql" --query 'value[0].message' -o tsv
```

**Result:** ✅ Schema file uploaded

### 11. Deploy Database Schema

```powershell
az vm run-command invoke -g DemoGoverno -n postgresql-vm --command-id RunShellScript --scripts "sudo -u postgres psql -d normas -f /tmp/models.sql 2>&1" --query 'value[0].message' -o tsv
```

**Result:** ✅ Schema deployed successfully

- CREATE EXTENSION (uuid-ossp, pg_trgm)
- CREATE TABLE (norma, admins)
- CREATE INDEX (6 indexes)
- CREATE FUNCTION (atualizar_data)
- CREATE TRIGGER (trg_atualizar_norma)

### 12. Verify Tables Created

```powershell
az vm run-command invoke -g DemoGoverno -n postgresql-vm --command-id RunShellScript --scripts "sudo -u postgres psql -d normas -c '\dt'" --query 'value[0].message' -o tsv
```

**Result:** ✅ Tables confirmed: `admins` and `norma`

---

## Database Setup Complete

### Summary

✅ PostgreSQL 14.20 running  
✅ Database `normas` created  
✅ User `linuxuser` created with password  
✅ Permissions granted  
✅ Schema deployed (2 tables, 6 indexes, 2 extensions, 1 function, 1 trigger)

### Connection Details

- Host: 20.226.39.175
- Port: 5432
- Database: normas
- User: linuxuser
- Password: r!(hFarm96g5Ayb3INF6

---

## Next Steps

- [x] Verify PostgreSQL is running ✅
- [x] Create `normas` database ✅
- [x] Configure database user and permissions ✅
- [x] Run schema from db/models.sql ✅
- [x] Create .env.example and .env.production ✅
- [x] Update deploy_azure.ps1 for DemoGoverno & GitHub ✅
- [x] Deploy API to Azure App Service ✅
- [x] Deploy Frontend to Azure Storage ✅
- [ ] Test API health endpoint
- [ ] Register first admin user

---

## 🎉 DEPLOYMENT COMPLETE

### Deployed Resources (DemoGoverno)

- **App Service Plan:** asp-gen360 (B1 Linux)
- **Web App (API):** app-gen360-api
- **Storage Account:** stgen360frontend (Static Website)
- **PostgreSQL VM:** postgresql-vm (already existing)

### URLs

- **API:** https://app-gen360-api.azurewebsites.net
- **API Health:** https://app-gen360-api.azurewebsites.net/health
- **API Docs:** https://app-gen360-api.azurewebsites.net/docs
- **Frontend:** https://stgen360frontend.z15.web.core.windows.net

### Deployment Summary

- **Date:** February 12, 2026 17:16 UTC
- **Build Time:** 135 seconds
- **Startup Time:** 506 seconds (~8.5 minutes)
- **Status:** RuntimeSuccessful
- **Files Uploaded:** 25 frontend files
- **Deployment Method:** Local ZIP upload

### Next Steps

1. Test API health endpoint
2. Update frontend API URL in app.js (if needed)
3. Register first admin user via frontend
4. Test database connectivity
5. Verify all admin functions

---

## Deployment Configuration

### Updated deploy_azure.ps1 Script

- **Resource Group:** DemoGoverno (existing)
- **PostgreSQL Host:** 20.226.39.175 (already configured)
- **Deployment Method:** Local ZIP upload (not GitHub)
- **Source:** Your current local code

### What Gets Packaged & Deployed

- `api/` - FastAPI application code
- `db/` - Database connection module
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification
- `startup.sh` - Startup script (if exists)

### Resources to Create in DemoGoverno

1. App Service Plan: asp-gen360 (Linux, B1)
2. Web App: app-gen360-api (Python 3.12)
3. Storage Account: stgen360frontend (static website)

---

## Environment Configuration

### Files Created

- **`.env.example`** - Template for environment variables
- **`setup/.env.production`** - Production configuration for Azure

### Environment Variables

```bash
# Database
DB_HOST=20.226.39.175
DB_PORT=5432
DB_NAME=normas
DB_USER=linuxuser
DB_PASSWORD=r!(hFarm96g5Ayb3INF6

# JWT
JWT_SECRET=Gen360-Azure-Production-Secret-Key-2026-Change-This
JWT_EXPIRE_MINUTES=60

# MFA
MFA_ISSUER=Gen360Admin

# CORS
CORS_ORIGINS=*
```

### Dependencies (requirements.txt)

- fastapi
- uvicorn
- pydantic
- psycopg2-binary
- gunicorn
- python-dotenv
