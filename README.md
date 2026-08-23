<div align="center">

<!-- Animated Header -->
<pre style="background: transparent;">
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ██████╗ ██╗   ██╗██████╗ ██╗████████╗███████╗                  ║
║   ██╔══██╗╚██╗ ██╔╝██╔══██╗██║╚══██╔══╝██╔════╝                  ║
║   ██████╔╝ ╚████╔╝ ██████╔╝██║   ██║   █████╗                    ║
║   ██╔═══╝   ╚██╔╝  ██╔══██╗██║   ██║   ██╔══╝                    ║
║   ██║        ██║   ██║  ██║██║   ██║   ███████╗                  ║
║   ╚═╝        ╚═╝   ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝                  ║
║                                                                  ║
║              The Dark-Side Text Editor for Hackers               ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
</pre>

<!-- Badges -->
<img src="https://img.shields.io/badge/Python-3.6+-1e1e1e?style=for-the-badge&logo=python&logoColor=d19a66&labelColor=252526">
<img src="https://img.shields.io/badge/GTK-3.0-1e1e1e?style=for-the-badge&logo=gtk&logoColor=56b6c2&labelColor=252526">
<img src="https://img.shields.io/badge/License-MIT-1e1e1e?style=for-the-badge&logo=opensourceinitiative&logoColor=98c379&labelColor=252526">
<img src="https://img.shields.io/badge/Vim-Mode-1e1e1e?style=for-the-badge&logo=vim&logoColor=e06c75&labelColor=252526">
<img src="https://img.shields.io/badge/Status-Fire-1e1e1e?style=for-the-badge&logo=fireship&logoColor=d19a66&labelColor=252526">

<br><br>

> *"A text editor so clean, it makes VS Code look like a cluttered desk."*

<br>

[🚀 Features](#-features) • [📸 Preview](#-preview) • [⚡ Installation](#-installation) • [⌨️ Keybindings](#-keybindings) • [🎨 Theming](#-theming)

</div>

---

## 🚀 Features

<table>
<tr>
<td width="50%">

### 🧠 Smart Editing
- **Auto-Indent** — Intelligent indentation that reads your code's soul
- **Smart Wrap** — `Alt+Z` to toggle word wrapping on the fly
- **Find & Highlight** — `Ctrl+F` with instant visual matches
- **Recent Files** — Remembers your last 5 files like a loyal companion

</td>
<td width="50%">

### ⚔️ Vim Mode
- **NORMAL / INSERT** — The way editing was meant to be
- **Command Mode** — `:w`, `:q`, `:wq` — all the classics
- **HJKL Navigation** — Leave the mouse behind
- **Visual Feedback** — Status bar shows your current mode in blazing color

</td>
</tr>
<tr>
<td width="50%">

### 🎨 Syntax Highlighting
- **Python-aware** — Keywords, strings, comments
- **Live Parsing** — Throttled to 300ms for buttery performance
- **One Dark Theme** — Atom-inspired color palette baked in
- **Zero Config** — Works out of the box

</td>
<td width="50%">

### 📜 Render Mode
- **Rich Text Preview** — Toggle side-pane rendering
- **Custom Tags** — `<bold>`, `<italic>`, `<ts=16>` for markup
- **Live Preview** — See your formatted output as you type
- **Split View** — Horizontal paned layout

</td>
</tr>
</table>

---

## 📸 Preview

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Options ▼]                                    [Render] [Vim: ON]  │
├─────────────────────────────────────────────────────────────────────┤
│  1  │ import os                                                      │
│  2  │ import sys                                                     │
│  3  │                                                                │
│  4  │ def main():                                                    │
│  5  │     print("Hello, PyRite!")                                     │
│  6  │                                                                │
│     │                                                                │
├─────────────────────────────────────────────────────────────────────┤
│ [NORMAL] main.py ●  |  Ln 4, Col 12  |  Words: 42  |  UTF-8   [4s]  │
└─────────────────────────────────────────────────────────────────────┘
```

> **Color Palette:** `#1e1e1e` background · `#d19a66` accents · `#56b6c2` keywords · `#98c379` strings · `#e06c75` modified indicator

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
# Clone the repository
git clone https://github.com/yourusername/pyrite.git
cd pyrite

# Run it
python3 PyRite.py
```

### Make it Global (Optional)

```bash
# Symlink to your local bin
chmod +x PyRite.py
ln -sf $(pwd)/PyRite.py ~/.local/bin/pyrite

# Now run from anywhere
pyrite
```

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
| `Esc` | Enter NORMAL Mode | Vim |
| `i` | Enter INSERT Mode | Vim (NORMAL) |
| `:w` | Save | Vim (COMMAND) |
| `:q` | Quit | Vim (COMMAND) |
| `:wq` | Save & Quit | Vim (COMMAND) |
| `h/j/k/l` | Navigate | Vim (NORMAL) |
| `x` | Delete char | Vim (NORMAL) |

---

## 🎨 Theming

PyRite ships with a carefully crafted **One Dark** aesthetic. No config files. No JSON nightmares. Just pure, unadulterated dark mode perfection.

| Element | Color | Hex |
|---------|-------|-----|
| Background | Deep Void | `#1e1e1e` |
| Surface | Elevated | `#252526` |
| Accent | Burnt Orange | `#d19a66` |
| Keywords | Cyan Ice | `#56b6c2` |
| Strings | Sage Green | `#98c379` |
| Modified Dot | Danger Red | `#e06c75` |
| Comments | Muted Grey | `#5c6370` |

---

## 🛠️ Configuration

PyRite stores its minimal state in:

```
~/.pyrite_recents.json    # Last 5 opened files
```

Everything else is **zero-config by design**. No `settings.json`. No plugin manager. Just you and the code.

---

## 🧪 Render Tags

When Render Mode is active, use these inline tags:

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

## 🤝 Contributing

1. Fork it
2. Create your feature branch: `git checkout -b feature/awesomeness`
3. Commit your changes: `git commit -am 'Add some awesomeness'`
4. Push to the branch: `git push origin feature/awesomeness`
5. Open a Pull Request

---

## 📜 License

MIT License — do whatever you want, just don't blame me when you get addicted.

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

**Made with 🔥 and zero Electron bloat.**

*[PyRite] — Because your code deserves a throne.*

</div>
