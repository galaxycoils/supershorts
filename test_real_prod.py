from src.modes.brainrot import run_brainrot_pipeline
from unittest.mock import MagicMock
import os

# Mock uploader to avoid browser opening
uploader = MagicMock()
uploader.upload.return_value = "DUMMY_ID_123"

# Run 1 short production
run_brainrot_pipeline(shorts_per_run=1, dry_run=False, uploader_service=uploader)
