# CHANGELOG

All notable changes to this project will be documented in this file.

## [0.0.27] - 2026-01-20

### Added
- **Backup Objects on Server**: New `--backup-objects` option to create per-object backup services directly on the Veeam server
  - Alternative to piggyback mode for environments where piggyback is not suitable
  - New check plugin `veeam_rest_backup_objects` with service name "Veeam Backup <object_name>"
  - Both options can be used simultaneously (piggyback AND server services)
- New GUI option "Create Backup Object Services on Server" in special agent configuration
- Additional metrics for backup objects:
  - `veeam_rest_backup_restore_points` - number of restore points
  - `veeam_rest_backup_avg_speed` - average backup speed
  - `veeam_rest_backup_total_size` - total size from progress
  - `veeam_rest_backup_backup_size` - backup size from restore point
  - `veeam_rest_backup_data_size` - data size from restore point

## [0.0.26] - 2026-01-20

### Fixed
- Added missing `check_parameters.py` to MKP manifest (fixes "static_checks:veeam_rest_license" error)

## [0.0.25] - 2026-01-19

### Added
- **Hybrid piggyback enrichment**: VM backups now include task data with richer metrics
  - Duration, processing speed, bottleneck info from task sessions
  - Additional size metrics (read size, transferred size, processed size)
  - Agent backups continue to work with backupObjects data only

## [0.0.24] - 2026-01-15

### Added
- Added `HyperVReplica` job type mapping for Hyper-V replication jobs

## [0.0.23] - 2026-01-15

### Changed
- **Piggyback now uses backupObjects API**: Switched from taskSessions to backupObjects endpoint
  - Works for ALL backup types (VMs AND Agent Backups)
  - Previously only VM backups generated piggyback data
- New fields available in backup status:
  - `lastRunFailed` - determines backup success/failure
  - `restorePointsCount` - number of available restore points
  - `type` and `platformName` - backup object type info
  - `originalSize` - size from latest restore point
  - `malwareStatus` - malware scan result from restore point

### Fixed
- Piggyback data now generated for Windows/Linux Agent Backups (not just VM backups)

## [0.0.22] - 2026-01-15

### Added
- **Piggyback support for VM backups**: New `--piggyback-vms` option attaches backup status to monitored VMs instead of creating services on the Veeam server
- New check plugin `veeam_rest_vm_backup` for processing piggyback backup data
- New ruleset option "Create Piggyback Data for VM Backups" in special agent configuration

### Changed
- Removed "tasks" from default sections (use piggyback instead for VM-level monitoring)
- Tasks section marked as legacy in ruleset UI

### Removed
- Removed `veeam_rest_tasks` check plugin (replaced by piggyback mechanism)

## [0.0.21] - 2026-01-15

### Added
- Documented limitation: Task sessions not available for Agent Backups (Windows/Linux)
- Added workaround guidance to use Job services instead of Task services for agent backups

## [0.0.20] - 2026-01-15

### Fixed
- Fixed speed metric parsing for Veeam API responses without `/s` suffix
- API returns `"131,9 MB"` instead of `"131,9 MB/s"` - parser now handles both formats
- Speed values now correctly display as MB/s or GB/s instead of B/s

## [0.0.19] - 2026-01-15

### Changed
- Renamed all metrics with `veeam_rest_` prefix to avoid naming conflicts with Checkmk core metrics
- Affected metrics:
  - Repository: `veeam_rest_repository_capacity`, `veeam_rest_repository_used`, `veeam_rest_repository_free`, `veeam_rest_repository_used_percent`
  - Jobs: `veeam_rest_job_duration`, `veeam_rest_job_size_processed`, `veeam_rest_job_size_read`, `veeam_rest_job_size_transferred`, `veeam_rest_job_speed`
  - Tasks: `veeam_rest_backup_age`, `veeam_rest_backup_duration`, `veeam_rest_backup_size_processed`, `veeam_rest_backup_size_read`, `veeam_rest_backup_size_transferred`, `veeam_rest_backup_speed`
  - License: `veeam_rest_license_days_remaining`, `veeam_rest_support_days_remaining`, `veeam_rest_license_instances_used`, `veeam_rest_license_instances_licensed`, `veeam_rest_license_instances_usage_percent`, `veeam_rest_license_sockets_used`, `veeam_rest_license_sockets_licensed`, `veeam_rest_license_capacity_used_tb`, `veeam_rest_license_capacity_licensed_tb`
  - WAN Accelerators: `veeam_rest_wan_accelerator_cache_size`, `veeam_rest_wan_accelerator_streams`

### Fixed
- Resolved metric naming conflict during Checkmk upgrade where `backup_age`, `backup_duration`, `job_duration` were already defined in Checkmk core

## [0.0.18] - 2026-01-15

### Changed
- Moved all helper functions to shared `lib.py`:
  - `parse_rate_to_bytes_per_second()` - rate string parsing
  - `parse_duration_to_seconds()` - duration string parsing
  - `format_duration_hms()` - duration formatting
- Jobs and Tasks checks now import all helpers from shared library

## [0.0.17] - 2026-01-15

### Changed
- Refactored shared helper functions to `lib.py` (DRY principle)
- `parse_rate_to_bytes_per_second()` now in shared library
- Jobs and Tasks checks import from `cmk_addons.plugins.veeam_rest.lib`

## [0.0.16] - 2026-01-15

### Added
- Backup speed metric (`backup_speed`) for Tasks/Backup services
- New "Veeam Backup Speed" graph for per-VM backup throughput
- Speed metric parsing for Tasks (same as Jobs)

## [0.0.15] - 2026-01-15

### Added
- Known Limitations section in README about REST API RBAC issues
- Documentation of Veeam's predefined roles limitations for monitoring
- Link to Veeam forum discussion about RBAC improvements

## [0.0.14] - 2026-01-13

### Removed
- Partial failure handling code from special agent
- `<<<veeam_rest_errors>>>` section output
- Let Checkmk handle missing sections natively

## [0.0.13] - 2026-01-13

### Added
- Contributors section in README
- Credit to [47k](https://github.com/47k) for extensive testing

## [0.0.12] - 2026-01-13

### Added
- Speed display in Job details (from API's `processingRate` field)
- Job processing speed metric (`job_speed`) for graphing
- New "Veeam Job Speed" graph showing backup throughput over time

### Changed
- Improved "Task not found" error message to indicate session age filtering
- Rate string parsing supports European decimal format (e.g., "1,1 GB/s")

## [0.0.11] - 2026-01-13

### Added
- Per-section caching to reduce API load
- Configurable cache intervals via GUI (Setup > Agents > Other integrations)
- `--cached-sections` and `--no-cache` CLI arguments
- Cache files stored in Checkmk tmp directory

### Cache Defaults
- Jobs: 5 minutes
- Tasks: 1 minute
- Sessions: 5 minutes
- Repositories: 30 minutes
- Proxies: 1 hour
- Managed Servers: 1 hour
- License: 24 hours
- Server Info: 24 hours
- Scale-Out Repositories: 30 minutes
- WAN Accelerators: 1 hour

## [0.0.10] - 2026-01-13

### Fixed
- License and Server rulesets now use HostCondition() for singleton services
- Fixes "rule does not match" display in Checkmk UI for Veeam License and Veeam Backup Server rules

## [0.0.9] - 2026-01-13

### Fixed
- Repository usage calculation now uses `capacity - free` instead of `usedSpaceGB` from API
- Fixes incorrect >100% usage display when Veeam reports logical data size instead of actual disk usage

## [0.0.8] - 2026-01-12

### Added
- Comprehensive README documentation with metrics and graphs tables
- Service output examples in documentation
- Default sections information and configuration guidance
- `--sections` CLI option documentation

### Changed
- Updated feature descriptions (jobs with duration & processed data display)
- Enhanced service descriptions with threshold display information
- Updated requirements to specify Veeam 13+ compatibility

## [0.0.7] - 2026-01-10

### Changed
- Removed old packages

### Added
- Performance data for jobs

## [0.0.5] - 2026-01-08

### Added
- Duration and processed metrics for jobs
- First implementation of localhost special agent

## [0.0.4] - 2026-01-08

### Added
- Localhost special agent concept

## [0.0.3] - 2026-01-02

### Changed
- Enhanced logging
- Removed unnecessary hostname option
- Updated README

### Removed
- Removed pyproject.toml and swagger.json from tracking

## [0.0.1] - 2025-11-28

### Added
- Initial release
- First alpha version
