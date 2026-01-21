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
- **Malware Detection** - Events and backup scan status combined
- **Piggyback Support** - Attach backup/malware services to monitored hosts
- **Performance Graphs** - Job duration, data transfer, repository usage trends

## Installation

See [Installation Guide](installation.md) for detailed setup instructions including Veeam user configuration and troubleshooting.

## Services Created

| Service | Description |
|---------|-------------|
| Veeam Job {type} - {name} | Backup job status, duration, processed data |
| Veeam Backup {object} | Per-object backup status, job name, restore points |
| Veeam Malware {machine} | Malware events + backup scan status combined |
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
| malware_events | No | Malware detection events |

## Rulesets

| Ruleset | Service | Parameters |
|---------|---------|------------|
| Veeam Backup Jobs | Veeam Job * | Job age, result/status state mapping |
| Veeam Backup (VM/Object) | Veeam Backup * | Backup age thresholds |
| Veeam Malware Events | Veeam Malware * | Malware status state mapping (Clean/Infected/Suspicious/NotScanned) |
| Veeam Repositories | Veeam Repository * | Usage levels, free space thresholds |
| Veeam License | Veeam License | Expiration thresholds, instance usage |

## Performance Optimization

### Restore Points Filter

For large environments with many VMs and long backup history, fetching all restore points can be slow (e.g., 12,000+ restore points = 100+ seconds). The agent filters restore points by age to dramatically improve performance:

| Setting | Default | Description |
|---------|---------|-------------|
| Restore Points Age | 7 days | Only fetch restore points from the last N days |

**Impact Example (105 VMs):**
- Without filter: 12,709 restore points, 104 seconds
- With 7-day filter: ~735 restore points, 3-5 seconds

Configure in: Setup > Agents > Other integrations > Veeam Backup & Replication (REST API)

**Note:** VMs without a backup in the configured time window will show no backup age, which can indicate a backup problem.

## Caching

The agent supports per-section caching to reduce API load:

| Section | Default Cache |
|---------|---------------|
| Jobs | 5 min |
| Repositories | 30 min |
| Proxies | 1 hour |
| Managed Servers | 1 hour |
| License | 24 hours |
| Server Info | 24 hours |
| Scale-Out Repos | 30 min |
| WAN Accelerators | 1 hour |
| Malware Events | 5 min |

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
