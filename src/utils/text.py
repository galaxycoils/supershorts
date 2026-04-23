import re
from typing import Optional

_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F680-\U0001F6FF"   # transport & map
    "\U0001F1E0-\U0001F1FF"   # flags
    "\U00002702-\U000027B0"   # dingbats
    "\U000024C2-\U0001F251"   # enclosed chars
    "\U0001F900-\U0001F9FF"   # supplemental symbols
    "\U0001FA00-\U0001FA6F"   # chess symbols
    "\U0001FA70-\U0001FAFF"   # symbols extended-A
    "\U00002300-\U000023FF"   # misc technical
    "]+",
    flags=re.UNICODE,
)

def strip_emojis(text: str) -> str:
    """Remove emoji and non-ASCII decorative chars before TTS."""
    text = _EMOJI_RE.sub('', text)
    return re.sub(r' {2,}', ' ', text).strip()

def strip_markdown(text: str) -> str:
    """Remove markdown formatting so TTS doesn't read 'asterisk asterisk'."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*',     r'\1', text, flags=re.DOTALL)
    text = re.sub(r'__(.+?)__',     r'\1', text, flags=re.DOTALL)
    text = re.sub(r'_(.+?)_',       r'\1', text, flags=re.DOTALL)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]*`', '', text)
    text = re.sub(r'^\s*[-•*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def clamp_words(text: str, min_w: int = 99, max_w: int = 127, pad_text: Optional[str] = None) -> str:
    """Pad/trim text to target word count range at sentence boundaries."""
    pad = pad_text or (
        " Most people never stop to think about this carefully. The science is clear "
        "and consistent on this topic. Understanding it gives you a real edge in today's "
        "world. Consistent small actions compound into dramatic results over time. "
        "The difference between those who succeed and those who struggle often comes down "
        "to awareness, consistency, and execution. Once you understand this principle, you "
        "cannot go back to ignoring it. Start applying it today and the results will "
        "genuinely surprise you over the next few months. Stay focused, stay consistent, "
        "and follow for more insights, tips, and advice like this every single week."
    )
    words = text.split()
    if len(words) < min_w:
        words += pad.split()
    if len(words) > max_w:
        words = words[:max_w]
    result = ' '.join(words)
    # Try to end on sentence boundary in last 30%
    for sep in ('. ', '! ', '? '):
        idx = result.rfind(sep)
        if idx > len(result) * 0.7:
            result = result[:idx + 1]
            break
    return result.strip()

def enforce_script_length(script: str, max_words: int = 1700) -> str:
    """Trim script at max_words. Minimum not enforced — avoids repetitive padding."""
    words = script.split()
    if len(words) > max_words:
        script = " ".join(words[:max_words])
    return script.strip()
