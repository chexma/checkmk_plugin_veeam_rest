# Veeam REST API Plugin for Checkmk

Checkmk 2.4 plugin for monitoring Veeam Backup & Replication servers via the REST API (v1.3).

## Features

- **Jobs** - Backup/replication job status, last result, schedule
- **Tasks** - Per-VM/object backup details with performance metrics
- **Repositories** - Capacity, usage levels, online status
- **Proxies** - Online/disabled/outdated status
- **Managed Servers** - vCenter, ESXi, Hyper-V host availability
- **License** - Status, expiration, instance usage
- **Scale-Out Repositories** - Extent health, tier status
- **WAN Accelerators** - Cache size, configuration

## Installation

```bash
mkp add veeam_rest-1.0.0.mkp
mkp enable veeam_rest 1.0.0
omd restart apache
```

## Configuration

1. **Setup > Agents > Other integrations > Veeam Backup & Replication**
2. Configure hostname, credentials (DOMAIN\user or user@domain), and sections to monitor
3. Run service discovery on the Veeam host

## Special Agent Usage

```bash
# Standard collection
./agent_veeam_rest --hostname 192.168.1.1 --username 'DOMAIN\admin' \
    --password secret --no-cert-check

# Redacted output for safe sharing
./agent_veeam_rest --hostname 192.168.1.1 --username 'DOMAIN\admin' \
    --password secret --no-cert-check --redact
```

The `--redact` flag anonymizes hostnames, paths, IDs, and descriptions while preserving metrics and status values for testing.

## Requirements

- Checkmk 2.4.0p1 or later
- Veeam Backup & Replication with REST API enabled (port 9419)
- User with REST API access permissions

## Services Created

| Service | Description |
|---------|-------------|
| Veeam Job {type} - {name} | Backup job status and results |
| Veeam Backup {vm} | Per-VM backup age and size |
| Veeam Repository {type} - {name} | Repository capacity and usage |
| Veeam Proxy {name} | Proxy online status |
| Veeam Server {name} | Managed server availability |
| Veeam License | License status and expiration |

## License

GPLv2
