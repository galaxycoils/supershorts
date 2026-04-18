import gc

def safe_close(*items) -> None:
    """Recursively close MoviePy clips and collect garbage."""
    for item in items:
        if not item: continue
        if isinstance(item, (list, tuple)):
            for sub in item: safe_close(sub)
        else:
            try:
                # Basic check for moviepy clip-like object
                if hasattr(item, 'close') and callable(item.close):
                    item.close()
            except Exception: pass
    gc.collect()
