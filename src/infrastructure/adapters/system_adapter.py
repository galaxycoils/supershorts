import subprocess
from typing import List, Optional, Any

class SystemAdapter:
    """Gateway adapter for system-level operations (subprocess, shell)."""
    
    def run_command(self, args: List[str], check: bool = True, capture_output: bool = True, **kwargs) -> subprocess.CompletedProcess:
        """Execute a system command."""
        return subprocess.run(args, check=check, capture_output=capture_output, **kwargs)

    def run_ffmpeg(self, input_args: List[str], output_args: List[str], loglevel: str = "error") -> subprocess.CompletedProcess:
        """Specialized helper for ffmpeg commands."""
        cmd = ["ffmpeg", "-y", "-loglevel", loglevel] + input_args + output_args
        return self.run_command(cmd)
