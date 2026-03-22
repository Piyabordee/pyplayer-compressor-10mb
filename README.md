# PyPlayer Compressor

> A modified fork of [PyPlayer](https://github.com/thisismy-github/pyplayer) with enhanced accessibility for quick video export.

**Original Project:** [thisismy-github/pyplayer](https://github.com/thisismy-github/pyplayer)
**Fork:** https://github.com/Piyabordee/pyplayer-compressor-10mb

---

## What's Changed

This fork includes UI enhancements for faster video editing workflow:

- **Always-visible Save Button** — The Save button is now permanently displayed in the quick actions row (next to the Next button), eliminating the need to activate trim mode first.
- **Quick Trim Button** — A single Trim button replaces the separate Start/End buttons. Click once to set trim start at current position (end automatically at video end), click again to cancel. The button displays the remaining duration when active.

---

## Features

PyPlayer is a powerful video player and editor built on VLC and PyQt5. Key capabilities include:

- **Video Editing:** Trim, crop, concatenate, fade, rotate/flip, and more
- **Audio Editing:** Amplify, replace tracks, add audio to images
- **Format Support:** MP4, MP3, WAV, AAC, GIF, and more
- **Quick Actions:** Instant file cycling, snapshots, rename/delete in place
- **Drag & Drop:** Drop files, folders, or subtitles directly into the player
- **Custom Themes:** Personalize with Qt Stylesheet themes

---

## Installation

### Requirements
- Python 3.13+
- VLC Media Player
- PyQt5

### Setup

```bash
# Clone this repository
git clone https://github.com/Piyabordee/pyplayer-compressor-10mb.git
cd pyplayer-compressor-10mb

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.pyw
```

### VLC Setup

Download VLC and place it in the `executable/include/` directory:
- **Windows:** Extract `vlc-windows` folder with `libvlc.dll` and `plugins`

---

## Usage

### Basic Controls
- **Open File:** Drag & drop or use File menu
- **Play/Pause:** Click on video player or press Space
- **Seek:** Click on progress bar or use arrow keys
- **Trim:** Click **Trim** button to set start at current position (end automatically at video end), then click **Save**. Click Trim again to cancel.
- **Crop:** Enable crop mode from menu, adjust borders
- **Snapshot:** Click camera icon to capture frame

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| Space | Play/Pause |
| ← → | Seek backward/forward |
| ↑ ↓ | Volume |
| F | Fullscreen |
| Delete | Mark file for deletion |

---

## Contributing

This is a personal fork for specific workflow improvements. For contributing to the original PyPlayer project, please visit [thisismy-github/pyplayer](https://github.com/thisismy-github/pyplayer).

---

## License

This project maintains the same license as the original PyPlayer. See [LICENSE](LICENSE) for details.

---

## Credits

All credit goes to [thisismy-github](https://github.com/thisismy-github) for creating PyPlayer. This fork simply adds UI convenience for specific use cases.

For the full feature set and documentation, please refer to the [original repository](https://github.com/thisismy-github/pyplayer).
