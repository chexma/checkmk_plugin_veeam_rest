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

Download the latest MKP file from the [GitHub Releases](https://github.com/chexma/checkmk_plugin_veeam_rest/releases) page.

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

### Create a Monitoring User

For security, create a dedicated, local Windows user for monitoring.

### Assign Veeam Permissions

1. Open **Veeam Backup & Replication Console**
2. Go to **Menu > Users and Roles**
3. Click **Add** and select your monitoring user
4. Assign the **Veeam Backup Viewer** role (read-only)

> **Note:** The Viewer role cannot access license information. Use **Veeam Backup Administrator** if you need license monitoring.

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

Test the special agent manually (optional):

```bash
# As site user
/omd/sites/<sitename>/local/lib/python3/cmk_addons/plugins/veeam_rest/libexec/agent_veeam_rest \
    --hostname veeam-server.local \
    --username 'DOMAIN\veeam_monitor' \
    --password 'SecurePassword123!' \
    --no-cert-check \
    --debug
```

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

**Impact on monitoring:**
- Task sessions provide backup metrics (size, duration, speed) for piggyback services
- Restore points provide malware scan status and latest backup time
- Does NOT affect Job services (they use the jobs API)
- Does NOT affect restore point count metrics (from backupObjects API)

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
Maximum Data Age: 24 hours

# For environments with hourly backups (reduce API load)
Maximum Data Age: 4 hours

# For environments with weekly backups
Maximum Data Age: 7 days
```

**Performance impact:**
- Without filter: 50,000+ task sessions + 12,000+ restore points → 130+ seconds
- With 24h filter: ~500 task sessions + ~500 restore points → ~4 seconds

---

### Caching

The special agent caches API responses to reduce load on the Veeam server.

**Default cache intervals (v0.0.50+):**

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

### Performance Summary

Optimal configuration for most environments:

| Setting | Value | Agent Runtime |
|---------|-------|---------------|
| Fetch Data From Last | 24 hours | ~4s (tasks + restore points) |
| Caching enabled | Yes (default) | Cache hit: ~0.5s |
| **Total (worst case)** | | **~8s** |
| **Total (typical)** | | **~0.5s** |

## Upgrading

To upgrade to a new version:

```bash
# Download new version
mkp add veeam_rest-X.Y.Z.mkp

# Disable old version, enable new
mkp disable veeam_rest 0.0.35
mkp enable veeam_rest X.Y.Z

# Restart services
omd restart apache
cmk -R
```

## Uninstalling

```bash
mkp disable veeam_rest 0.0.35
mkp remove veeam_rest 0.0.35
omd restart apache
```

Don't forget to remove the special agent rule and re-discover services on affected hosts.
