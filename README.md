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
mkp add veeam_rest-0.0.3.mkp
mkp enable veeam_rest 0.0.3
omd restart apache
```

## Configuration

1. **Setup > Agents > Other integrations > Veeam Backup & Replication**
2. Configure hostname, credentials (DOMAIN\user or user@domain), and sections to monitor
3. Run service discovery on the Veeam host

## Special Agent Usage

```bash
# Standard collection (silent)
./agent_veeam_rest --hostname 192.168.1.1 --username '.\user' \
    --password secret --no-cert-check

# With verbosity for troubleshooting
./agent_veeam_rest --hostname 192.168.1.1 --username '.\user' \
    --password secret --no-cert-check -vv

# Redacted output for safe sharing
./agent_veeam_rest --hostname 192.168.1.1 --username '.\user' \
    --password secret --no-cert-check --redact
```

### CLI Options

| Option | Description |
|--------|-------------|
| `-v` | Show section summaries and warnings |
| `-vv` | + API endpoints and item counts |
| `-vvv` | + Request timing and pagination details |
| `--debug` | Show Python stack traces on errors |
| `--redact` | Anonymize hostnames, paths, IDs for safe sharing |

### Partial Failure Handling

The agent continues collecting data even if individual sections fail. Failed sections are reported in a `<<<veeam_rest_errors>>>` section, allowing partial monitoring when specific API endpoints are unavailable.

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
