# Veeam REST API Plugin for Checkmk

Checkmk 2.4 plugin for monitoring Veeam Backup & Replication (Version 13 and above) servers via the REST API.

## Features

- **Jobs** - Backup/replication job status with duration & processed data display
- **Backup Objects** - Per-VM/agent backup status with restore point info
- **Repositories** - Capacity, usage levels, online status with perfometer
- **Proxies** - Online/disabled/outdated status
- **Managed Servers** - vCenter, ESXi, Hyper-V host availability
- **License** - Status, expiration, instance usage with threshold display
- **Scale-Out Repositories** - Extent health, tier status
- **WAN Accelerators** - Cache size, configuration
- **Malware Status** - Backup scan status (Clean/Infected/Suspicious) in backup services
- **Piggyback Support** - Attach backup services to monitored hosts
- **Performance Graphs** - Job duration, data transfer, repository usage trends

## Installation

See [Installation Guide](installation.md) for detailed setup instructions including Veeam user configuration and troubleshooting.

## Services Created

| Service | Description |
|---------|-------------|
| Veeam Job {type} - {name} | Backup job status, duration, processed data |
| Veeam Backup {object} | Per-object backup status, malware scan, restore points |
| Veeam Repository {name} | Repository capacity and usage |
| Veeam Proxy {name} | Proxy online status |
| Veeam Server {name} | Managed server availability |
| Veeam License | License status, expiration with thresholds |
| Veeam Backup Server | Backup server information |
| Veeam SOBR {name} | Scale-out backup repository status |
| Veeam WAN {name} | WAN accelerator status |

## Sections

| Section | Default | Description |
|---------|---------|-------------|
| jobs | Yes | Backup job states |
| repositories | Yes | Repository capacity |
| proxies | Yes | Proxy status |
| managed_servers | No | Managed infrastructure |
| license | No | License information |
| server | No | Backup server info |
| scaleout_repositories | No | Scale-out repositories |
| wan_accelerators | No | WAN accelerators |

## Rulesets

| Ruleset | Service | Parameters |
|---------|---------|------------|
| Veeam Backup Jobs | Veeam Job * | Job age, result/status state mapping |
| Veeam Backup (VM/Object) | Veeam Backup * | Backup age, malware status state mapping |
| Veeam Repositories | Veeam Repository * | Usage levels, free space thresholds |
| Veeam License | Veeam License | Expiration thresholds, instance usage |

## Performance Optimization

### Fetch Data From Last

Controls how far back the agent fetches task sessions and restore points. Set based on your backup frequency:

| Backup Frequency | Recommended Value |
|------------------|-------------------|
| Daily backups | 24 hours (default) |
| Weekly backups | 7 days |
| Bi-weekly backups | 14 days |

**Performance Impact:**
- Without filter: 50,000+ sessions + 12,000+ restore points → 130+ seconds
- With 24h filter: ~500 sessions + ~500 restore points → ~4 seconds

Configure in: Setup > Agents > Other integrations > Veeam Backup & Replication (REST API) > "Fetch Data From Last"

## Caching

The agent caches API responses to reduce load. Default intervals optimized for typical use:

| Section | Default Cache | Reason |
|---------|---------------|--------|
| Jobs | 30 min | Backups run hourly/daily |
| Backup Objects | 30 min | Slow API, backups run hourly/daily |
| Repositories | 5 min | Fast API, capacity changes matter |
| Proxies | 5 min | Fast API, status important |
| Managed Servers | 1 hour | Rarely changes |
| License | 24 hours | Rarely changes |
| Server Info | 24 hours | Rarely changes |
| Scale-Out Repos | 5 min | Fast API |
| WAN Accelerators | 5 min | Fast API |

Configure custom intervals via GUI or disable with `--no-cache`.

## Requirements

- Checkmk 2.4.0p1 or later
- Veeam Backup & Replication 13+ with REST API enabled (port 9419)
- User with REST API access permissions

## Known Limitations

### REST API Permissions (RBAC)

The Veeam B&R REST API currently lacks granular role-based access control (RBAC). Only predefined roles are available:

- **Veeam Backup Administrator** - Full access but not recommended for security
- **Veeam Backup Viewer** - Read-only but lacks access to some data (e.g., license)

See: [Veeam Forums Discussion](https://forums.veeam.com/post561632.html#p561632)

## Contributors

- [47k](https://github.com/47k) - Thanks for extensive testing!

## License

GPLv2
