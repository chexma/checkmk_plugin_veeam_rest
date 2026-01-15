#!/usr/bin/env python3
"""
Shared utility functions for Veeam REST monitoring plugin.
"""


def parse_rate_to_bytes_per_second(rate_str: str) -> float | None:
    """Parse rate string like '1,1 GB/s' or '500 MB/s' to bytes/second."""
    if not rate_str:
        return None
    try:
        # Handle European decimal format (1,1 -> 1.1)
        rate_str = rate_str.replace(",", ".")
        parts = rate_str.split()
        if len(parts) != 2:
            return None
        value = float(parts[0])
        unit = parts[1].upper()
        multipliers = {
            "B/S": 1,
            "KB/S": 1024,
            "MB/S": 1024**2,
            "GB/S": 1024**3,
            "TB/S": 1024**4,
        }
        return value * multipliers.get(unit, 1)
    except (ValueError, IndexError):
        return None


def parse_duration_to_seconds(duration_str: str) -> int | None:
    """Parse duration string like '00:03:26' or '1.00:03:26' to seconds."""
    if not duration_str:
        return None
    try:
        parts = duration_str.split(":")
        if len(parts) == 3:
            # Check if first part contains days (e.g., "1.00")
            hours_part = parts[0]
            if "." in hours_part:
                days_str, hours_str = hours_part.split(".", 1)
                days = int(days_str)
                hours = int(hours_str)
            else:
                days = 0
                hours = int(hours_part)
            minutes = int(parts[1])
            seconds = int(parts[2])
            return days * 86400 + hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        pass
    return None


def format_duration_hms(seconds: int) -> str:
    """Format duration as HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
