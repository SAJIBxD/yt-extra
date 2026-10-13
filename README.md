# yt-extra

Extra [yt-dlp](https://github.com/yt-dlp/yt-dlp#readme) extractors.

Requires yt-dlp `2025.12.08` or above.

## Installation

> **Note:** `pip install` only works when yt-dlp itself is installed in that
> same Python environment (pip/pipx installs). It does **not** work with the
> Homebrew formula or the standalone `yt-dlp` binary, which run in an
> isolated environment — use the manual method instead.

### Manual install (recommended — works with any yt-dlp, incl. brew/standalone)

Copy the `yt_dlp_plugins` directory from this repo into yt-dlp's plugin
folder, so the final layout is
`<plugins>/yt_dlp_plugins/extractor/*.py`. The plugin folder is:

- Linux: `~/.config/yt-dlp/plugins/`
- macOS: `~/Library/Application Support/yt-dlp/plugins/`
- Windows: `%APPDATA%\yt-dlp\plugins\`

```sh
git clone https://github.com/SAJIBxD/yt-extra
# Linux example:
mkdir -p ~/.config/yt-dlp/plugins
cp -r yt-extra/yt_dlp_plugins ~/.config/yt-dlp/plugins/
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
