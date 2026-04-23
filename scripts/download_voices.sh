#!/bin/bash
# Download basic Piper voice files

VOICE_DIR=~/.local/share/piper-tts/voices
mkdir -p "$VOICE_DIR"

echo "Downloading Piper ONNX voices..."

# List of requested voices
VOICES=(
  "en_US-ryan-high"
  "en_US-lessac-high"
  "en_US-amy-medium"
  "en_GB-alan-medium"
  "en_US-hfc_female-medium"
  "en_US-joe-medium"
  "en_US-kristin-medium"
  "en_GB-northern_english_male-medium"
  "en_US-libritts-high"
)

BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en"

for voice in "${VOICES[@]}"; do
  # Extract components (e.g., en_US -> en/en_US)
  LANG_CODE=$(echo "$voice" | cut -d'-' -f1)
  QUALITY=$(echo "$voice" | rev | cut -d'-' -f1 | rev)
  NAME=$(echo "$voice" | sed "s/${LANG_CODE}-//" | sed "s/-${QUALITY}//")
  
  DIR_LANG=$(echo "$LANG_CODE" | tr '_' '-')
  URL_PATH="${BASE_URL}/${DIR_LANG}/${NAME}/${QUALITY}/${voice}.onnx"
  JSON_URL="${URL_PATH}.json"
  
  if [ ! -f "$VOICE_DIR/${voice}.onnx" ]; then
    echo "Downloading ${voice}..."
    curl -LL -s -o "$VOICE_DIR/${voice}.onnx" "$URL_PATH"
    curl -LL -s -o "$VOICE_DIR/${voice}.onnx.json" "$JSON_URL"
  else
    echo "Voice ${voice} already exists."
  fi
done

echo "Done downloading voices!"
