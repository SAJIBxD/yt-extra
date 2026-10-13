# yt-extra

Extra [yt-dlp](https://github.com/yt-dlp/yt-dlp#readme) extractors.

Requires yt-dlp `2025.12.08` or above.

## Installation

> **Note:** `pip install` only works when yt-dlp itself is installed in that
> same Python environment (pip/pipx installs). It does **not** work with the
> Homebrew formula or the standalone `yt-dlp` binary, which run in an
> isolated environment — use the manual method instead.

### Manual install (recommended — works with any yt-dlp, incl. brew/standalone)

Clone this repo inside yt-dlp's plugin folder, so the final layout is
`<plugins>/yt-extra/yt_dlp_plugins/extractor/*.py` (the extra folder level
matters). The plugin folder is:

- Linux/macOS: `~/.config/yt-dlp/plugins/` (or `$XDG_CONFIG_HOME/yt-dlp/plugins/`)
- Windows: `%APPDATA%\yt-dlp\plugins\`
- Fallback on any OS: `~/.yt-dlp/plugins/`

```sh
# Linux/macOS example:
mkdir -p ~/.config/yt-dlp/plugins
git clone https://github.com/SAJIBxD/yt-extra ~/.config/yt-dlp/plugins/yt-extra
```

### Via pip (only if yt-dlp was installed with pip/pipx in the same environment)

```sh
python3 -m pip install -U https://github.com/SAJIBxD/yt-extra/archive/main.zip
```

If yt-dlp was installed with pipx:

```sh
pipx inject yt-dlp https://github.com/SAJIBxD/yt-extra/archive/main.zip
```

### One-off use without installing

```sh
git clone https://github.com/SAJIBxD/yt-extra
PYTHONPATH=/path/to/yt-extra yt-dlp "URL"
# or:
yt-dlp --plugin-dirs /path/to/yt-extra "URL"
```

## Development

See the [Plugin Development](https://github.com/yt-dlp/yt-dlp/wiki/Plugin-Development) section of the yt-dlp wiki.
