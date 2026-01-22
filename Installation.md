# Installation Guide

## Prerequisites

### Checkmk Server
- Checkmk 2.4.0p1 or later (Cloud, Enterprise, or Raw Edition)
- Network access to Veeam server on port 9419 (HTTPS)

### Veeam Backup & Replication Server
- Version 13 or higher
- REST API enabled (default on port 9419)
- User account with API access

## Step 1: Download the Plugin

Download the latest MKP file from the [GitHub](https://github.com/chexma/checkmk_plugin_veeam_rest/) page.

Or copy the MKP file directly to your Checkmk server:

```bash
scp veeam_rest-0.0.35.mkp user@checkmk-server:/tmp/
```

## Step 2: Install the Plugin

Connect to your Checkmk server and switch to the site user:

```bash
ssh user@checkmk-server
sudo su - <sitename>
```

Install and enable the plugin:

```bash
mkp add /tmp/veeam_rest-0.0.35.mkp
mkp enable veeam_rest 0.0.35
```

Restart the Apache service to load the new rulesets:

```bash
omd restart apache
```

Verify the installation:

```bash
mkp list
# Should show: veeam_rest 0.0.35
```

## Step 3: Configure Veeam REST API Access

### Enable REST API (if not already enabled)

The REST API is enabled by default in Veeam B&R 13+. Verify it's running:

1. On the Veeam server, open **Veeam Backup & Replication Console**
2. Go to **Menu > Options > RESTful API**
3. Ensure the service is enabled on port 9419

### Create a Monitoring User (Security Best Practices)

Following the **principle of least privilege**, create a dedicated user account exclusively for Veeam monitoring:

1. **Create a local Windows user** on the Veeam server (not a domain admin!)
   - Use a descriptive name like `svc_checkmk_veeam` or `veeam_monitor`
   - Use a strong, unique password
   - Disable interactive logon if possible

2. **Do NOT use:**
   - Domain Administrator accounts
   - The Veeam service account
   - Shared accounts used for other purposes
   - Personal user accounts

### Assign Veeam Permissions

1. Open **Veeam Backup & Replication Console**
2. Go to **Menu > Users and Roles**
3. Click **Add** and select your monitoring user
4. Assign the **Veeam Backup Viewer** role

**Available Roles:**

| Role | Access Level | Recommendation |
|------|--------------|----------------|
| **Veeam Backup Viewer** | Read-only access to jobs, repositories, proxies | Recommended for monitoring |
| **Veeam Backup Operator** | Viewer + can start/stop jobs | Not needed for monitoring |
| **Veeam Backup Administrator** | Full access including license info | Only if license monitoring required |

### Role Limitations & Security Recommendation

> **Security Recommendation:** Use the **Veeam Backup Viewer** role. Avoid using Administrator until Veeam implements granular RBAC.

The **Veeam Backup Viewer** role is the most secure choice but has limitations:

- Cannot access license information (license section will be empty)
- Cannot view some advanced configuration details

**Why avoid the Administrator role?**

The Veeam REST API currently lacks granular role-based access control (RBAC). There is no "Viewer + License" role available. Using the Administrator role for monitoring grants unnecessary write permissions (create/delete jobs, modify configurations), which violates security best practices.

**Recommendation:** Accept the license monitoring limitation and use the Viewer role until Veeam delivers granular RBAC support. Monitor license expiration through other means (e.g., Veeam email notifications).

See [Veeam Forums Discussion](https://forums.veeam.com/post561632.html#p561632) for the RBAC feature request.

## Step 4: Add the Veeam Host to Checkmk

1. Go to **Setup > Hosts > Add host**
2. Enter the Veeam server hostname or IP
3. Configure appropriate agent settings (can use "No API integrations, no Checkmk agent")
4. Save the host

## Step 5: Store Password in Password Store (Recommended)

For security, store the Veeam user password in Checkmk's password store instead of entering it directly in the rule:

1. Go to **Setup > General > Passwords**
2. Click **Add password**
3. Configure:
   - **Unique ID**: `veeam_rest_api` (or similar)
   - **Title**: `Veeam REST API`
   - **Password**: Enter the Veeam monitoring user password
4. Save

> **Why use the password store?** Passwords in the store are encrypted at rest and not visible in the rule configuration. This prevents accidental exposure when sharing configurations or taking screenshots.

## Step 6: Configure the Special Agent

1. Go to **Setup > Agents > Other integrations > Veeam Backup & Replication (REST API)**
2. Click **Add rule**
3. Configure the connection:

| Setting | Value |
|---------|-------|
| **Hostname/IP** | Veeam server address |
| **Port** | 9419 (default) |
| **Username** | `username` |
| **Password** | Select "From password store" and choose `veeam_rest_api` |
| **SSL Verification** | Disable if using self-signed certificate |

4. Select **Sections to Collect**:
   - Jobs (default)
   - Repositories (default)
   - Proxies (default)
   - License (optional)
   - Managed Servers (optional)
   - etc.

5. Configure **Backup Services** mode:
   - **Disabled** - No per-object backup services
   - **Attach to Hosts** - Piggyback services on VMs (requires VMs in Checkmk)
   - **Attach to Backup Server** - Services on Veeam server

6. Set **Explicit hosts** to your Veeam server hostname

7. Save the rule

## Step 7: Run Service Discovery

1. Go to your Veeam host in Checkmk
2. Click **Run service discovery**
3. Accept the discovered services
4. Activate changes

## Step 8: Verify the Setup

Check that services are discovered:

| Service | Status |
|---------|--------|
| Veeam Job Backup - Daily | OK |
| Veeam Repository Default | OK |
| Veeam Proxy veeam-proxy01 | OK |
| Veeam License | OK |

## Troubleshooting

### "Connection refused" or timeout

1. Check firewall: Port 9419 must be open from Checkmk to Veeam
2. Verify REST API is running on Veeam server
3. Test connectivity:
   ```bash
   curl -k https://veeam-server:9419/api/v1/serverInfo
   ```

### "401 Unauthorized"

1. Verify username format: `DOMAIN\user` or `user@domain`
2. Check user has Veeam REST API permissions
3. Test authentication manually:
   ```bash
   curl -k -X POST https://veeam-server:9419/api/oauth2/token \
       -H "Content-Type: application/x-www-form-urlencoded" \
       -H "x-api-version: 1.3-rev1" \
       -d "grant_type=password&username=DOMAIN%5Cuser&password=secret"
   ```

### "SSL certificate verify failed"

Enable "Disable SSL certificate verification" in the special agent rule, or install the Veeam server's certificate as trusted on the Checkmk server.

### No services discovered

1. Check the special agent output in **Service > Check Veeam data source**
2. Verify sections are enabled in the rule
3. Ensure the Veeam server has jobs/repositories configured

### Piggyback services not appearing

1. The target VMs must exist as hosts in Checkmk
2. VM names in Veeam must match hostnames in Checkmk (case-insensitive)
3. Run discovery on the VM hosts, not just the Veeam server

## Performance Tuning

### Fetch Data From Last

**Location:** Setup > Agents > Other integrations > Veeam Backup & Replication (REST API)

**What it does:**
This single filter controls the age of both **task sessions** AND **restore points** that are fetched from the Veeam API.

- **Task sessions** contain per-VM/object details for each backup run (status, duration, size, warnings)
- **Restore points** are the actual backup snapshots used to get malware status and latest backup info

**Default:** 24 hours (86400 seconds)

**Recommended values - set based on your backup frequency:**

| Backup Frequency | Recommended Value | In Seconds |
|------------------|-------------------|------------|
| Hourly backups | 2-4 hours | 7200-14400 |
| Daily backups | 24-48 hours | 86400-172800 |
| Weekly backups | 7-14 days | 604800-1209600 |
| Bi-weekly backups | 14-21 days | 1209600-1814400 |

**Examples:**

```
# For environments with daily backups (default)
Fetch Data From Last: 24 hours

# For environments with hourly backups (reduce API load)
Fetch Data From Last: 4 hours

# For environments with weekly backups
Fetch Data From Last: 7 days
```

**Performance impact:**
- Without filter: 50,000+ task sessions + 12,000+ restore points → 130+ seconds
- With 24h filter: ~500 task sessions + ~500 restore points → ~4 seconds

---

### Caching

The special agent caches API responses to reduce load on the Veeam server.

**Default cache intervals:**

| Section | Cache Time | Reason |
|---------|------------|--------|
| Jobs | 30 min | Backups typically run hourly/daily |
| Backup Objects | 30 min | Slow API (~6s), matches job frequency |
| Repositories | 5 min | Fast API, capacity changes important |
| Proxies | 5 min | Fast API, status important |
| Scale-Out Repos | 5 min | Fast API |
| WAN Accelerators | 5 min | Fast API |
| Managed Servers | 1 hour | Rarely changes |
| License | 24 hours | Rarely changes |
| Server Info | 24 hours | Rarely changes |

**Custom cache intervals:**

Configure via GUI under "Cache Intervals per Section" in the special agent rule.

**Disable caching:**

Enable "Disable Caching" option for always-fresh data (increases API load significantly).

---
