# TCM Audio Fix Plan

## Changes
- Remove the `audio_clip.close()` call and its surrounding `try/except` block inside the loop in `src/generator.py` where `final_clip` is constructed. This prevents the audio stream from being prematurely closed before `write_videofile` uses it.

## Verification
- Run the workflow/script to generate a TCM video and verify that it completes without the `'NoneType' object has no attribute 'get_frame'` error.