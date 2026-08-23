<div align="center">

<!-- Animated Header -->
<pre style="background: transparent;">
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║          ██████╗ ██╗   ██╗██████╗ ██╗████████╗███████╗           ║
║          ██╔══██╗╚██╗ ██╔╝██╔══██╗██║╚══██╔══╝██╔════╝           ║
║          ██████╔╝ ╚████╔╝ ██████╔╝██║   ██║   █████╗             ║
║          ██╔═══╝   ╚██╔╝  ██╔══██╗██║   ██║   ██╔══╝             ║
║          ██║        ██║   ██║  ██║██║   ██║   ███████╗           ║
║          ╚═╝        ╚═╝   ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝           ║
║                                                                  ║
║                A Minimal Dark-Mode Text Editor                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
</pre>

<!-- Badges -->
<img src="https://img.shields.io/badge/Python-3.6+-1e1e1e?style=for-the-badge&logo=python&logoColor=d19a66&labelColor=252526">
<img src="https://img.shields.io/badge/GTK-3.0-1e1e1e?style=for-the-badge&logo=gtk&logoColor=56b6c2&labelColor=252526">
<img src="https://img.shields.io/badge/License-MIT-1e1e1e?style=for-the-badge&logo=opensourceinitiative&logoColor=98c379&labelColor=252526">
<img src="https://img.shields.io/badge/Status-Early_Development-1e1e1e?style=for-the-badge&logo=fireship&logoColor=d19a66&labelColor=252526">

<br><br>

> A single-file GTK3 text editor with a One Dark theme, basic modal editing, and zero config files.

<br>

[🚀 Features](#-features) • [⚡ Installation](#-installation) • [⌨️ Keybindings](#-keybindings) • [🎨 Theming](#-theming) • [🧭 Known Limitations](#-known-limitations)

</div>

---

## 🚀 Features

<table>
<tr>
<td width="50%">

### 🧠 Editing
- **Auto-Indent** — continues indentation after a line ending in `:`
- **Word Wrap** — `Alt+Z` to toggle
- **Find & Highlight** — `Ctrl+F`, live match highlighting
- **Recent Files** — remembers your last 5 files

</td>
<td width="50%">

### ⌨️ Modal Editing
- **NORMAL / INSERT** toggle via `Esc` / `i`
- **Command Mode** — `:w`, `:q`, `:wq`
- **HJKL Navigation** and `x` to delete a character
- *(This is a lightweight modal layer, not a vim clone — see [Known Limitations](#-known-limitations))*

</td>
</tr>
<tr>
<td width="50%">

### 🎨 Syntax Highlighting
- **Python-aware** — keywords, strings, comments
- **Debounced** to 300ms so it doesn't lag on large files
- **One Dark** color palette, on by toggle

</td>
<td width="50%">

### 📜 Render Mode
- **Inline markup preview** in a side pane
- **Custom tags** — `<bold>`, `<italic>`, `<ts=16>`
- Rebuilds when you toggle Render on (not live as you type yet)

</td>
</tr>
</table>

---

## ⚡ Installation

### Prerequisites

```bash
# Debian / Ubuntu
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Arch Linux
sudo pacman -S python-gobject gtk3

# Fedora
sudo dnf install python3-gobject gtk3
```

### Clone & Run

```bash
git clone https://github.com/SulphArk/PyRite.git
cd PyRite
python3 PyRite.py
```

### Make it Global (Optional)

```bash
chmod +x PyRite.py
ln -sf $(pwd)/PyRite.py ~/.local/bin/pyrite
pyrite
```
> Requires a `#!/usr/bin/env python3` shebang at the top of `PyRite.py` to run directly as `pyrite` — add it if it's not already there.

---

## ⌨️ Keybindings

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl + O` | Open File | Global |
| `Ctrl + S` | Save File | Global |
| `Ctrl + N` | New File | Global |
| `Ctrl + F` | Find | Global |
| `Ctrl + R` | Toggle Render | Global |
| `Alt + Z` | Toggle Word Wrap | Global |
| `Esc` | Enter NORMAL Mode | Modal |
| `i` | Enter INSERT Mode | Modal (NORMAL) |
| `:w` | Save | Modal (COMMAND) |
| `:q` | Quit | Modal (COMMAND) |
| `:wq` | Save & Quit | Modal (COMMAND) |
| `h / j / k / l` | Navigate | Modal (NORMAL) |
| `x` | Delete char | Modal (NORMAL) |

---

## 🎨 Theming

| Element | Color | Hex |
|---------|-------|-----|
| Background | Deep Void | `#1e1e1e` |
| Surface | Elevated | `#252526` |
| Accent | Burnt Orange | `#d19a66` |
| Keywords | Cyan Ice | `#56b6c2` |
| Strings | Sage Green | `#98c379` |
| Modified Dot | Danger Red | `#e06c75` |
| Comments | Muted Grey | `#5c6370` |

No config files — the palette is baked into a single CSS block in the source.

---

## 🛠️ Configuration

PyRite stores minimal state in:

```
~/.pyrite_recents.json    # Last 5 opened files
```

Everything else is zero-config by design.

---

## 🧪 Render Tags

| Tag | Effect |
|-----|--------|
| `<bold>text</bold>` | **Bold text** |
| `<italic>text</italic>` | *Italic text* |
| `<ts=20>text</ts=20>` | Custom font size |

---

## 🏗️ Architecture

```
PyRiteEditor (Gtk.Window)
├── Top Bar
│   ├── Options MenuButton
│   └── Vim Toggle | Render Button
├── Gtk.Paned
│   ├── Editor Box
│   │   ├── Line Numbers (TextView)
│   │   └── Source View (TextView + ScrolledWindow)
│   └── Render View (TextView + ScrolledWindow)
├── Find Bar (Revealer)
└── Status Bar
    ├── Mode | Filename | Modified
    └── Indent Toggle
```

---

## 🧭 Known Limitations

This is early-stage software. Being upfront about what's missing:

- **No undo/redo** — plain `Gtk.TextBuffer` doesn't provide this for free; needs either `GtkSource.Buffer` or a manual undo stack.
- **Modal editing is minimal** — no `dd`, yank/paste, word motions, counts, or visual mode. Think "basic navigation layer," not a vim clone.
- **No unsaved-changes prompt** — closing, opening a new file, or `:q` will discard edits without warning.
- **File I/O doesn't force UTF-8 encoding** — the status bar always shows "UTF-8" but reads/writes use the system locale default.
- **Render pane isn't live** — it rebuilds when toggled, not as you type.
- **No packaging** — no `pyproject.toml`/`setup.py`; install is manual symlink only.

Contributions welcome on any of the above.

---

## 🤝 Contributing

1. Fork it
2. Create your feature branch: `git checkout -b feature/awesomeness`
3. Commit your changes: `git commit -am 'Add some awesomeness'`
4. Push to the branch: `git push origin feature/awesomeness`
5. Open a Pull Request

---

## 📜 License

MIT License — see [LICENSE](LICENSE).

```
Copyright (c) 2026 PyRite Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<div align="center">

<br>

**A small editor, honestly described.**

</div>
