from src.modes.brainrot import run_brainrot_pipeline
import os

# Set dummy environment variables if needed
os.environ["OLLAMA_MODEL"] = "llama3.2:3b"

# Run a dry run for 1 short
run_brainrot_pipeline(shorts_per_run=1, dry_run=True)
