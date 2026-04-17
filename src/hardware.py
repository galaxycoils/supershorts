"""Host capability detection — tunes the pipeline for the current machine.

Primary motivation: an M1 MacBook Pro with 8 GB unified RAM can blow through
available memory if we spin up 4 parallel Piper processes + MoviePy
CompositeVideoClip on a 1080x1920 frame at once. Detecting that host and
dropping to 2 workers + a smaller encode buffer keeps peak RAM under ~4 GB.
"""
import functools
import os
import platform

# Hosts with <= this many GB of RAM use low-memory settings.
# M1 8 GB typically reports ~8.0 GB via SC_PHYS_PAGES; 16 GB machines
# report ~16.0. 10 GB is a safe fence between the two.
_LOW_MEM_THRESHOLD_GB = 10.0


@functools.lru_cache(maxsize=1)
def total_ram_gb() -> float:
    """Return total physical RAM in GB. Falls back to 16 on unknown systems
    so we don't accidentally enable low-mem mode on a healthy server."""
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return pages * page_size / (1024 ** 3)
    except (OSError, ValueError, AttributeError):
        pass
    # Fallback for macOS via sysctl (sysconf is reliable there, but belt+braces)
    try:
        import subprocess
        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=2)
        return int(out.strip()) / (1024 ** 3)
    except Exception:
        return 16.0


@functools.lru_cache(maxsize=1)
def is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


@functools.lru_cache(maxsize=1)
def is_low_mem() -> bool:
    """Engage low-memory mode?

    Auto-detect via total RAM; override either way with SUPERSHORTS_LOW_MEM
    (set to "1" to force on, "0" to force off).
    """
    override = os.environ.get("SUPERSHORTS_LOW_MEM")
    if override == "1":
        return True
    if override == "0":
        return False
    return total_ram_gb() <= _LOW_MEM_THRESHOLD_GB


def max_parallel_slides() -> int:
    """How many TTS + slide renders can run in parallel without OOM?"""
    if is_low_mem():
        return 2
    cores = os.cpu_count() or 4
    return min(4, cores)


def encoder_bitrate() -> str:
    """Target bitrate for hardware h264 encode.

    Lower bitrate → smaller ring buffers in videotoolbox, less peak RAM.
    6M gives visually lossless shorts at 1080p; 4M is still above the
    YouTube recommended 2.5 Mbps for 1080p SDR.
    """
    return "4M" if is_low_mem() else "6M"


def describe() -> str:
    """One-line summary, printed once on startup for sanity."""
    flavour = "low-mem" if is_low_mem() else "standard"
    return (
        f"host: {platform.machine()} {platform.system()} "
        f"({total_ram_gb():.1f} GB RAM, {os.cpu_count()} CPUs) "
        f"→ {flavour} profile, {max_parallel_slides()} parallel slides"
    )
