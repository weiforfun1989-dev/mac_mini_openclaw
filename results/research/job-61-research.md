# Research: Alibaba Voice Cloning (Qwen3-TTS + Voicebox)

**Task:** #61  
**Date:** 2026-02-23  
**Status:** ✅ Complete

---

## Overview

Alibaba's voice cloning technology consists of two main components:

### 1. Qwen3-TTS (Backend)
- **Developer:** Alibaba Cloud (Qwen team)
- **License:** Apache 2.0 (Open Source)
- **GitHub:** https://github.com/QwenLM/Qwen3-TTS
- **Features:**
  - Text-to-speech synthesis
  - Voice cloning from few seconds of audio
  - Multi-language support
  - Streaming speech generation
  - Emotional tone control

### 2. Voicebox (Frontend/Desktop App)
- **Developer:** Jamie Pine (community wrapper)
- **GitHub:** https://github.com/jamiepine/voicebox
- **Website:** https://voicebox.sh/
- **Features:**
  - Desktop GUI for Qwen3-TTS
  - Local processing (no cloud)
  - Voice cloning from 3-10 seconds of audio
  - Multi-voice project composition
  - Studio-grade editing tools
  - Metal acceleration (Mac) / CUDA (Windows/Linux)

---

## Installation

### Option 1: Desktop App (Recommended)
```bash
# Downloaded and installed to:
/Applications/Voicebox.app

# Size: 287 MB
# Requirements: macOS 11+ (Apple Silicon)
```

**Location:** `/Users/wxia/.openclaw/workspace/voice-clone/Voicebox.dmg`

### Option 2: Python API (Advanced)
```bash
# Clone repository
git clone https://github.com/QwenLM/Qwen3-TTS.git

# Install (Note: dependency conflicts may occur)
pip install git+https://github.com/QwenLM/Qwen3-TTS.git
```

**Issue:** accelerate==1.12.0 dependency not available for current Python version.

---

## How to Use

### Voicebox GUI App:
1. Launch `/Applications/Voicebox.app`
2. Download a voice model (first run)
3. Import audio sample (3-10 seconds)
4. Clone the voice
5. Type text to generate speech
6. Export audio file

### Use Cases:
- Audiobook narration
- Voice assistants
- Accessibility tools
- Content creation
- Voiceovers

---

## Capabilities

| Feature | Description |
|---------|-------------|
| **Voice Cloning** | Clone any voice from 3-10 seconds of audio |
| **Real-time** | Fast inference with Metal/CUDA acceleration |
| **Local** | 100% local processing, no data leaves your machine |
| **Multi-voice** | Compose projects with multiple cloned voices |
| **Emotional** | Control emotional tone of generated speech |

---

## Comparison with Alternatives

| Tool | Cloud | Local | Open Source | Cost |
|------|-------|-------|-------------|------|
| **Voicebox/Qwen3-TTS** | ❌ | ✅ | ✅ | Free |
| ElevenLabs | ✅ | ❌ | ❌ | $5-330/mo |
| Play.ht | ✅ | ❌ | ❌ | $31-99/mo |
| Coqui TTS | ❌ | ✅ | ✅ | Free |

---

## Files

- Voicebox DMG: `/Users/wxia/.openclaw/workspace/voice-clone/Voicebox.dmg`
- Installed App: `/Applications/Voicebox.app`
- Python venv: `/Users/wxia/.openclaw/workspace/voice-clone/venv`

---

## Next Steps

1. ✅ Research complete
2. ✅ Voicebox installed
3. ⏭️ Launch Voicebox.app to test voice cloning
4. ⏭️ Create sample audio for testing
5. ⏭️ Integrate with job dispatch system (optional)

---

## References

- Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS
- Voicebox: https://github.com/jamiepine/voicebox
- Voicebox Website: https://voicebox.sh/
