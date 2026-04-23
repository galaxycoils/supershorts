# Fixes Plan: UI Restoration & Headless Uploading

## 1. Fix Missing Modes
The previous update renamed the modes to match RotGen perfectly (e.g., "Teaches", "Storytelling"). I will restore the original SuperShorts modes (Educational/TCM, Brainrot, RotGen, Tutorial, Viral, Clipper, Ideas) in `static/js/main.js` while keeping the new sleek card-based RotGen UI design.

## 2. Fix Blank Modal & "Auto Generate"
The multi-step modal logic was oversimplified. I will rewrite `renderStep()` in `static/js/main.js` to dynamically inject the correct input fields based on the selected mode:
- **Brainrot:** Restore the "Topic / Hook (Auto-generate from viral trends)" input.
- **TCM:** Restore the "Topic Focus", "Custom Topic", and "Sub-topics" fields.
- **Clipper/Tutorial/Viral:** Restore their specific URL and topic inputs.
This will ensure the modal is never blank and all required inputs are present.

## 3. Force Headless Uploading
I will update `src/infrastructure/browser_uploader.py` to force `options.add_argument("--headless")` globally, regardless of the operating system (macOS/Linux/Windows), ensuring background uploads do not pop up browser windows.

## 4. Addressing the 8-Line Error
The chat interface stripped your pasted text (replacing it with `[Pasted Text: 8 lines]`). I need to see those errors to fix them. Once I exit Plan Mode, I will ask you to provide the error or I will check the terminal logs directly.

## Execution
I will execute these fixes in parallel, utilizing subagents where possible to review the JavaScript and Python updates for quality and correctness.