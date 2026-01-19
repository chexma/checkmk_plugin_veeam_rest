# Veeam REST API Plugin for Checkmk

Checkmk 2.4 plugin for monitoring Veeam Backup & Replication (Version 13 and above) servers via the REST API.

## Features

- **Jobs** - Backup/replication job status with duration & processed data display
- **Tasks** - Per-VM/object backup details with performance metrics
- **Repositories** - Capacity, usage levels, online status with perfometer
- **Proxies** - Online/disabled/outdated status
- **Managed Servers** - vCenter, ESXi, Hyper-V host availability
- **License** - Status, expiration, instance usage with threshold display
- **Scale-Out Repositories** - Extent health, tier status
- **WAN Accelerators** - Cache size, configuration
- **Performance Graphs** - Job duration, data transfer, repository usage trends

## Installation

```bash
mkp add veeam_rest-0.0.8.mkp
mkp enable veeam_rest 0.0.8
omd restart apache
```

## Configuration

1. **Setup > Agents > Other integrations > Veeam Backup & Replication (REST API)**
2. Configure hostname, credentials (DOMAIN\user or user@domain), and sections to monitor
3. Run service discovery on the Veeam host

## Services Created

| Service | Description |
|---------|-------------|
| Veeam Job {type} - {name} | Backup job status, duration, processed data |
| Veeam Backup {vm} | Per-VM backup age and size |
| Veeam Repository {name} | Repository capacity and usage |
| Veeam Proxy {name} | Proxy online status |
| Veeam Server {name} | Managed server availability |
| Veeam License | License status, expiration with thresholds |
| Veeam SOBR {name} | Scale-out backup repository status |
| Veeam WAN {name} | WAN accelerator status |

## Requirements

- Checkmk 2.4.0p1 or later
- Veeam Backup & Replication 13+ with REST API enabled (port 9419)
- User with REST API access permissions

## Known Limitations

### REST API Permissions (RBAC)

The Veeam B&R REST API currently lacks granular role-based access control (RBAC). Only predefined roles are available, which are not well suited for monitoring use cases:

- **Veeam Backup Administrator** - Has full access but should not be used for security reasons
- **Veeam Backup Viewer** - Read-only but lacks access to critical monitoring data (e.g., license information)

There is currently no way to create a dedicated monitoring user with minimal required permissions. As a workaround, you may need to use an Administrator account or accept limited monitoring capabilities with the Viewer role.

Veeam has acknowledged this limitation and is working on a solution, but no timeframe has been provided. See: [Veeam Forums Discussion](https://forums.veeam.com/post561632.html#p561632)

### Task Sessions for Agent Backups

The Veeam REST API `/api/v1/taskSessions` endpoint does **not** return data for **Windows/Linux Agent Backups**. Task sessions are only populated for VM-based backups (vSphere, Hyper-V, etc.).

**Impact:** "Veeam Backup {hostname}" services will show UNKNOWN for agent-based backups because no task session data is available.

**Workaround:** Use the **Job services** ("Veeam Job Windows Agent - {jobname}") instead, which correctly show status, duration, and result for agent backup jobs. If you have discovered task services for agent backups, remove them with:

```bash
cmk -II hostname  # Re-discover services
cmk -R
```

## Contributors

- [47k](https://github.com/47k) - Thanks for extensive testing of the plugin!

## License

GPLv2
