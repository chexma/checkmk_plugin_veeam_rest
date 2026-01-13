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

### Default Sections

By default, only these sections are collected:
- `jobs`, `tasks`, `repositories`, `proxies`

To enable additional monitoring, explicitly select in the rule:
- `license` - License status and expiration
- `server` - Backup server information
- `managed_servers` - Managed infrastructure
- `scaleout_repositories` - Scale-out backup repositories
- `wan_accelerators` - WAN accelerators

## Service Output Examples

```
# Job with duration and processed data
Veeam Job VMware Backup - Daily: Status: inactive, Last result: Success, Last Duration: 00:03:26, Processed: 68.2 GB

# License with threshold display
Veeam License: License status: Valid, License expires in 45 days (warn/crit below 30/7 days), Instance usage: 50/100 (50.0%) (warn/crit at 80/95%)

# Repository with usage
Veeam Repository Default - Backup: Used: 1.5 TB of 4.0 TB (37.5%)
```

## Metrics & Graphs

### Job Metrics
| Metric | Description |
|--------|-------------|
| `job_duration` | Job duration in seconds |
| `job_size_processed` | Processed data size |
| `job_size_read` | Read data size |
| `job_size_transferred` | Transferred data size |

### Repository Metrics
| Metric | Description |
|--------|-------------|
| `repository_capacity` | Total repository size |
| `repository_used` | Used space |
| `repository_free` | Free space |
| `repository_used_percent` | Usage percentage |

### License Metrics
| Metric | Description |
|--------|-------------|
| `license_days_remaining` | Days until license expiration |
| `support_days_remaining` | Days until support expiration |
| `license_instances_usage_percent` | Instance usage percentage |

### Available Graphs
- **Veeam Job Duration** - Job duration over time
- **Veeam Job Data Transfer** - Processed/read/transferred data
- **Veeam Repository Usage** - Repository space usage
- **Veeam License Expiration** - License and support days remaining

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

# Include all sections
./agent_veeam_rest --hostname 192.168.1.1 --username '.\user' \
    --password secret --no-cert-check \
    --sections jobs tasks repositories proxies license server managed_servers
```

### CLI Options

| Option | Description |
|--------|-------------|
| `-v` | Show section summaries and warnings |
| `-vv` | + API endpoints and item counts |
| `-vvv` | + Request timing and pagination details |
| `--debug` | Show Python stack traces on errors |
| `--redact` | Anonymize hostnames, paths, IDs for safe sharing |
| `--sections` | Specify which sections to collect |

### Partial Failure Handling

The agent continues collecting data even if individual sections fail. Failed sections are reported in a `<<<veeam_rest_errors>>>` section, allowing partial monitoring when specific API endpoints are unavailable.

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
