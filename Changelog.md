# CHANGELOG

All notable changes to this project will be documented in this file.

## [0.0.49] - 2026-01-22

### Removed
- **Special Agent Ruleset Cleanup**: Removed all malware-related GUI options
  - Removed "Malware Detection Events" from sections
  - Removed "Malware Services" mode selector
  - Removed "Malware Events" cache interval
  - Renamed "Maximum Task/Malware Event Age" to "Maximum Task Session Age"

## [0.0.48] - 2026-01-22

### Changed
- **Malware Status Simplification**: Replaced separate malware events with integrated backup malware status
  - Malware status now shown directly in Veeam Backup services: `Malware scan: Clean`
  - Status comes from `latestRestorePoint.malwareStatus` field (no extra API call)
  - Configurable state mapping via new `malware_status_states` parameter in Veeam Backup ruleset
  - Defaults: Clean=OK, Infected=CRIT, Suspicious=WARN, NotScanned=WARN

### Removed
- **Malware Events Plugin**: Removed `veeam_rest_malware_events.py` check plugin
- **Malware Events API**: Removed `/api/v1/malwareDetection/events` API calls from agent
- **--malware-mode Option**: Removed from special agent (no longer needed)
- **Malware Events Section**: Removed `malware_events` and `malware_combined` cache sections
- **Debug Script**: Removed malware events endpoint test

### Added
- **Last Run/Next Run in Jobs**: Added formatted dates to job service details
  - Format: DD.MM.YYYY HH:MM:SS (e.g., "22.01.2026 14:30:00")
  - Shown in service details for scheduled jobs

## [0.0.47] - 2026-01-22

### Fixed
- **Critical: Backup Objects Filter**: Fixed filter that removed ALL backup objects
  - The `backupId` field doesn't exist in `/api/v1/backupObjects` API response
  - Changed filter to use name prefix "outdated_" instead
  - This restores all backup object services that disappeared in 0.0.44/0.0.45

### Changed
- **Piggyback Hostname**: Removed automatic lowercase conversion
  - Hostnames now keep original case, only spaces are replaced with underscores
  - Example: `KGM-SEAL-01` instead of `kgm-seal-01`

## [0.0.46] - 2026-01-21

### Added
- **Restore Points Thresholds**: New parameters for Veeam Backup services
  - `restore_points_min_warn` / `restore_points_min_crit`: Alert if restore points below threshold
  - `restore_points_max_warn` / `restore_points_max_crit`: Alert if restore points exceed threshold
  - Useful for detecting backup retention issues or missing backups
  - Applies to both piggyback and server-side backup services
- **Restore Points Metric**: Added `veeam_rest_backup_restore_points` metric to piggyback services

## [0.0.45] - 2026-01-21

### Added
- **Caching for Backup Objects**: Added caching for `backup_objects` section (5 minutes default)
  - Caches the enriched backup objects data (including restore points and task sessions)
  - Reduces API load significantly in large environments
  - Previously backup objects were fetched fresh on every agent run
  - Cache can be disabled with `--no-cache` flag

## [0.0.44] - 2026-01-21

### Fixed
- **Filter Orphaned Backup Objects**: Exclude "outdated_" backup objects from discovery
  - Objects without `backupId` are now filtered out (orphaned/old backups)
  - These objects had `restorePointsCount > 0` but no active job association
  - Prevents "Veeam Backup outdated_*" services from being created

## [0.0.43] - 2026-01-21

### Fixed
- **Performance: Task Sessions Filter**: Fixed slow task session fetching for warning detection
  - Task sessions now filtered by `createdAfterFilter` parameter (uses `--session-age` setting)
  - Previously fetched ALL task sessions which caused major slowdowns in large environments
  - Example: 50,000 task sessions → ~500 (24h filter) = ~100x faster

### Added
- **Debug Script**: New warning detection test section
  - Shows jobs with Warning/Failed status
  - Tests task sessions performance (filtered vs unfiltered)
  - Lists VMs with warning/failed task results
  - Helps diagnose warning detection issues

## [0.0.42] - 2026-01-21

### Fixed
- **VM-specific Job Warnings/Errors**: Fixed warning detection to use task sessions instead of session logs
  - Session logs don't contain per-VM warning details in a parseable format
  - Now uses task sessions API (`/api/v1/taskSessions`) to find VMs with Warning/Failed results
  - Correctly matches task sessions to their parent job session
  - VMs with warning/failed task results now properly show WARNING/CRITICAL state

## [0.0.41] - 2026-01-21

### Added
- **VM-specific Job Warnings/Errors**: Backup services now show issues from job session logs
  - Fetches session logs for jobs with Warning or Failed result
  - Only affected VMs show WARNING/CRITICAL (e.g., VSS writer failures)
  - Warning jobs → WARN state, Failed jobs → CRIT state
  - Full error message displayed in service details
  - New API method: `get_session_logs()` using `/api/v1/sessions/{id}/logs`

## [0.0.40] - 2026-01-21

### Changed
- **Malware Events Service Output**: Moved detailed file location info to service details
  - Summary now shows only: event type, severity, source, age
  - Full details (file paths, detected patterns) visible in service details view
  - Improves readability in service lists

## [0.0.39] - 2026-01-21

### Fixed
- **Malware Events Detection**: Fixed machine name extraction using `displayName` instead of `name`
  - API returns machine names in `displayName` field, not `name`
  - Previously all events were grouped under "Unknown" instead of actual machine names
- **Duplicate Section Output**: Fixed duplicate `<<<veeam_rest_malware_events>>>` section when both `malware_events` section and `malware_mode` are enabled
  - Now only outputs enriched malware data when `malware_mode` is set
  - Prevents parser conflicts from two sections with same name

## [0.0.38] - 2026-01-21

### Changed
- **Renamed Option**: "Maximum Session/Task Age" → "Maximum Task/Malware Event Age"
  - Clarifies that this filters task sessions (for backup metrics) and malware events
  - Sessions section was removed in 0.0.33, name was outdated

## [0.0.37] - 2026-01-21

### Changed
- **Major Performance Fix**: Optimized `get_backup_objects_with_job_info()` function
  - Now uses bulk endpoints instead of per-backup API calls
  - **Before**: 35 API calls (1 + 34 per backup), ~34-340 seconds
  - **After**: 2 API calls, ~1-2 seconds
  - Uses `/api/v1/backupObjects` bulk endpoint + `/api/v1/backups` for job mapping
  - Joins data in Python instead of making individual API calls per backup

## [0.0.36] - 2026-01-21

### Added
- **Restore Points Time Filter**: New `--restore-points-days` parameter (default: 7 days)
  - Filters restore points by creation time using `createdAfterFilter` API parameter
  - Dramatically improves performance in large environments
  - **Example**: 12,709 restore points → 2,765 restore points (~78% reduction)
  - **Time saved**: 104 seconds → 6 seconds (~94% faster)
  - Configurable via GUI: "Restore Points Age (Days)" in special agent settings
  - Set to 0 to disable filtering (not recommended for large environments)

### Changed
- **Debug Script**: Updated `debug_veeam_api.py` with restore points filter
  - New `--restore-points-days` CLI option
  - Performance test now uses filtered bulk API call
  - Shows filter timestamp in output

## [0.0.35] - 2026-01-20

### Changed
- **Major Performance Optimization**: Bulk restore point fetching
  - New `get_all_restore_points()` API method fetches ALL restore points in 1-5 calls
  - Replaces ~500 individual `get_object_restore_points()` calls per VM
  - Matching by object name in Python instead of per-object API calls
  - **Result: ~495 fewer API calls, ~50 seconds faster for 500 VMs**
- **Performance Optimization**: Deduplicated backup object enrichment
  - `enrich_backup_objects()` now called only once when both backup_mode and malware_mode are enabled
  - Prevents duplicate restore point fetching when both modes active

## [0.0.34] - 2026-01-20

### Added
- **Caching for Malware Services**: Added caching for `--malware-mode` (Attach to Hosts/Backup Server)
  - Combined malware data now cached for 5 minutes (default)
  - Reduces API load when malware services are enabled
  - New cache key `malware_combined` for enriched malware data

## [0.0.33] - 2026-01-20

### Added
- **Installation Guide**: New `installation.md` with step-by-step setup instructions
  - Prerequisites and Veeam REST API configuration
  - Password store usage recommendation for secure credential storage
  - Troubleshooting section for common issues
  - Upgrade and uninstall instructions

### Removed
- **Removed unused sections**: `tasks` and `sessions` sections removed from GUI
  - These sections output data but no check plugin consumed them
  - Task data is still fetched internally for backup object enrichment
  - Simplifies configuration by removing non-functional options

## [0.0.32] - 2026-01-20

### Changed
- **Dropdown Menus for Service Output**: Replaced checkbox options with dropdown menus for cleaner configuration
  - New `backup_mode` dropdown with options: Disabled, Attach to Hosts, Attach to Backup Server
  - New `malware_mode` dropdown with options: Disabled, Attach to Hosts, Attach to Backup Server
  - Only one option can be selected at a time (mutually exclusive)
  - Default is "Disabled" for both dropdowns
- **New CLI Arguments**: Replaced `--piggyback-vms`, `--backup-objects`, `--piggyback-malware` with:
  - `--backup-mode` (choices: piggyback-vms, backup-server)
  - `--malware-mode` (choices: piggyback-hosts, backup-server)
- **Consolidated Malware Monitoring**: Combined malware data sources for unified monitoring
  - Malware events service now shows both: detection events AND backup scan status (malwareStatus)
  - Removed malware status display from backup services (Veeam Backup <object>)
  - Moved `malware_status_states` ruleset parameter from "Veeam Backup" to "Veeam Malware Events"
  - Agent enriches malware events with restore point malware status for combined view

## [0.0.31] - 2026-01-20

### Added
- **Job Name in Backup Services**: Backup object services now display which backup job they belong to
  - Service summary shows "Job: <job_name>" for both server and piggyback services
  - New API method fetches backup objects per backup to get job association
  - Works for VM backups, agent backups, and all other backup types

### Changed
- **Unified Backup Services**: Piggyback and server-side backup services are now consistent
  - Piggyback service renamed from "Veeam Backup" to "Veeam Backup <object_name>"
  - Both service types now use the same ruleset "Veeam Backup (VM/Object)"
  - Only one rule needed to configure both piggyback and server services
  - Old rulesets "Veeam VM Backup (Piggyback)" and "Veeam Backup Objects (Server)" removed

### Fixed
- **Malware Events Piggyback**: Fixed output format for piggyback malware events
  - Was outputting dict format instead of list format expected by parser
  - Piggyback malware services now work correctly
- **Orphaned Backup Objects**: VMs removed from backup jobs no longer create services
  - Objects with `restorePointsCount == 0` are now filtered out
  - Prevents "No restore points" WARN services for VMs no longer being backed up

## [0.0.30] - 2026-01-20

### Added
- **Piggyback for Malware Events**: New `--piggyback-malware` option to attach malware events to affected hosts
  - Services created on the affected hosts instead of the Veeam server
  - New GUI option "Create Piggyback Data for Malware Events"
  - Can be used together with `malware_events` section (both server and piggyback)

## [0.0.29] - 2026-01-20

### Added
- **Malware Detection Events Section**: New `malware_events` section to monitor Veeam's malware detection events
  - Shows which machines have been flagged as suspicious/infected
  - Tracks confirmed false positives (marked as clean)
  - New check plugin `veeam_rest_malware_events` with service "Veeam Malware <machine>"
  - Displays event details: type, severity, source, detection time
  - Metrics: total events, active events, false positives
- New API endpoint: `/api/v1/malwareDetection/events`

## [0.0.28] - 2026-01-20

### Added
- **Configurable Malware Status**: Malware scan results can now be mapped to custom monitoring states via rulesets
  - New ruleset "Veeam VM Backup (Piggyback)" for piggyback services
  - New ruleset "Veeam Backup Objects (Server)" for server services
- New default behavior for malware status:
  - `Suspicious` → WARNING (previously OK)
  - `NotScanned` → WARNING (previously no output)
  - `Infected` → CRITICAL (unchanged)
  - `Clean` → OK (unchanged)

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
