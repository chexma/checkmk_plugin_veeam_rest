# CHANGELOG

All notable changes to this project will be documented in this file.

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
