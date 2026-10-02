

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
- **Replicas** - Disaster recovery replica monitoring (vSphere/Hyper-V)
- **Configuration Backup** - Veeam config backup status with age thresholds
- **Security Compliance** - Best practice violations and security checks
- **Malware Status** - Backup scan status (Clean/Infected/Suspicious) in backup services
- **Piggyback Support** - Attach backup services to monitored hosts
- **Performance Graphs** - Job duration, data transfer, repository usage trends

## Installation

See [Installation Guide](Installation.md) for detailed setup instructions including Veeam user configuration and troubleshooting.

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
| Veeam Replica {name} | DR replica status (vSphere/Hyper-V) |
| Veeam Config Backup | Configuration backup status and age |
| Veeam Security Compliance | Security best practice check results |

## Sections

All sections are enabled by default. See [Installation Guide](Installation.md#available-sections) for permission requirements per section.

## Rulesets

| Ruleset | Service | Parameters |
|---------|---------|------------|
| Veeam Backup Jobs | Veeam Job * | Job age, result/status state mapping |
| Veeam Backup (VM/Object) | Veeam Backup * | Backup age, malware status state mapping |
| Veeam Repositories | Veeam Repository * | Usage levels, free space thresholds |
| Veeam License | Veeam License | Expiration thresholds, instance usage |
| Veeam Configuration Backup | Veeam Config Backup | Backup age thresholds (default: 7/14 days) |
| Veeam Security Compliance | Veeam Security Compliance | Failed checks thresholds (default: 1/5) |

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

### Tape Job Support

The Veeam B&R REST API currently lacks information about Tape Jobs.
This will also be added in a future release.

### Restore Point Counts Span All Backup Chains

The `Restore points` value reported per VM/object is Veeam's own `restorePointsCount`
from `/api/v1/backupObjects`. It counts **all** restore points of that object across
every backup chain on the server - primary job, backup copy jobs, GFS points and
leftover backups of deleted jobs. It is therefore not comparable to the retention of a
single job. Tape is never included (the REST API exposes no tape data).

Run `debug_veeam_api.py --analyze-restore-points <name>` to see the breakdown per
backup chain.

## Contributors

- [47k](https://github.com/47k) - Thanks for extensive testing!

## License

GPLv2
