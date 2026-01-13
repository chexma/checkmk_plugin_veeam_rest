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

## Contributors

- [47k](https://github.com/47k) - Thanks for extensive testing of the plugin!

## License

GPLv2
