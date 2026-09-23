<div align="center">

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

<img src="https://img.shields.io/badge/Python-3.6+-1e1e1e?style=for-the-badge&logo=python&logoColor=d19a66&labelColor=252526">
<img src="https://img.shields.io/badge/GTK-3.0-1e1e1e?style=for-the-badge&logo=gtk&logoColor=56b6c2&labelColor=252526">
<img src="https://img.shields.io/badge/GtkSourceView-4.0-1e1e1e?style=for-the-badge&logo=gnome&logoColor=4a86cf&labelColor=252526">
<img src="https://img.shields.io/badge/License-MIT-1e1e1e?style=for-the-badge&logo=opensourceinitiative&logoColor=98c379&labelColor=252526">
<img src="https://img.shields.io/badge/Status-Production-1e1e1e?style=for-the-badge&logo=fireship&logoColor=61a03c&labelColor=252526">

<br><br>

> A single-file GTK3 text editor built on GtkSourceView4 with a dark theme,
> full vim emulation, and zero config.

<br>

[🚀 Features](#-features) • [⌨️ Keybindings](#-keybindings) • [🎨 Theming](#-theming) • [📦 Installation](#-installation)

</div>

---

## 🚀 Features

<table>
<tr>
<td width="50%">

### 🧠 Editing
- **Undo / Redo** - 100-level undo stack via GtkSourceView4
- **Auto-Indent** - continues indentation after `:`
- **Word Wrap** -`Alt+Z` to toggle
- **Find & Replace** - `Ctrl+F`, live highlighting, replace one/all
- **Recent Files** - remembers your last 10 files
- **File Monitoring** - detects external changes, prompts reload
- **Drag & Drop** - drop files onto the window to open

</td>
<td width="50%">

### ⌨️ Modal Editing (Vim)
- **NORMAL / INSERT** toggle via `Esc` / `i`
- **Command Mode** — `:w`, `:q`, `:wq`, `:q!`
- **HJKL Navigation** with count prefixes (`5j`)
- **Word Motions** — `w`, `b`, `e`
- **Line Ops** — `dd` (delete), `yy` (yank), `p` (paste)
- **Undo / Redo** — `u` / `Ctrl+R`
- **Goto** — `gg` (top), `G` (bottom), `0`/`$` (line start/end)
- **New** — `o`, `O`, `A`, `a` for insert variants

</td>
</tr>
<tr>
<td width="50%">

### 🎨 Syntax Highlighting
- **Auto-detect** language from file extension
- **60+ languages** via GtkSourceView4
- **Oblivion** dark color scheme, baked in
- **Bracket matching** highlighted

</td>
<td width="50%">

### 📜 Render Mode
- **Inline markup preview** in a side pane
- **Custom tags** — `<bold>`, `<italic>`, `<ts=16>`
- Rebuilds when toggled on

</td>
</tr>
</table>

---

## ⌨️ Keybindings

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl + O` | Open File | Global |
| `Ctrl + S` | Save File | Global |
| `Ctrl + N` | New File | Global |
| `Ctrl + F` | Find & Replace | Global |
| `Ctrl + R` | Toggle Render | Global |
| `Ctrl + Z` | Undo | Global |
| `Ctrl + Y` | Redo | Global |
| `Alt + Z` | Toggle Word Wrap | Global |
| `Esc` | Enter NORMAL Mode | Vim |
| `i` | Enter INSERT Mode | Vim (NORMAL) |
| `a` / `A` | Insert after char / end of line | Vim (NORMAL) |
| `o` / `O` | Open line below / above | Vim (NORMAL) |
| `:w` | Save | Vim (COMMAND) |
| `:q` | Quit | Vim (COMMAND) |
| `:wq` | Save & Quit | Vim (COMMAND) |
| `:q!` | Force Quit | Vim (COMMAND) |
| `h / j / k / l` | Navigate | Vim (NORMAL) |
| `w / b / e` | Word forward/back/end | Vim (NORMAL) |
| `x` | Delete char | Vim (NORMAL) |
| `dd` | Delete line | Vim (NORMAL) |
| `yy` | Yank line | Vim (NORMAL) |
| `p` | Paste | Vim (NORMAL) |
| `u` | Undo | Vim (NORMAL) |
| `Ctrl+R` | Redo | Vim (NORMAL) |
| `gg` / `G` | Go to top / bottom | Vim (NORMAL) |
| `0` / `$` | Go to line start / end | Vim (NORMAL) |
| `V` | Select line | Vim (NORMAL) |

---

## 🎨 Theming

| Element | Color | Hex |
|---------|-------|-----|
| Background | Deep Void | `#101315` |
| Surface | Elevated | `#0c0e10` |
| Accent | User-chosen | `#61A03C` (default) |
| Keywords | Green | `#8fbd6b` |
| Strings | Sage | `#b9cdad` |
| Comments | Muted | `#5c6a58` |
| Modified Dot | Accent | user-chosen |

Accent color is user-configurable via Options → Accent Color. Stored in:

```
~/.config/pyrite/accent.json
```

---

## 📦 Installation

### Prerequisites

```bash
# Arch Linux
sudo pacman -S python-gobject gtk3 gtksourceview4

# Debian / Ubuntu
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtksource-4

# Fedora
sudo dnf install python3-gobject gtk3 gtksourceview4
```

### Clone & Run

```bash
git clone https://github.com/SulphArk/PyRite.git
cd PyRite
python3 PyRite.py
```

### Make it Global

```bash
chmod +x PyRite.py
ln -sf $(pwd)/PyRite.py ~/.local/bin/pyrite
pyrite myfile.py
```

### Desktop Integration

```bash
cp pyrite.desktop ~/.local/share/applications/
cp pyrite.svg ~/.local/share/icons/hicolor/scalable/apps/
```

---

## 🏗️ Architecture

```
PyRiteEditor (Gtk.Window)
├── Top Bar
│   ├── Options MenuButton
│   └── Vim Toggle | Render Button
├── GtkSourceView (syntax, undo, line numbers)
├── Render View (TextView + ScrolledWindow)
├── Search Bar (Revealer)
│   ├── Search Entry
│   ├── Replace Entry
│   └── Replace One / Replace All / Close
└── Status Bar
    ├── Mode | Filename | Modified
    └── Indent Toggle
```

---

## 📝 Configuration

PyRite stores minimal state in:

```
~/.config/pyrite/recents.json    # Last 10 opened files
~/.config/pyrite/accent.json     # User accent color
```

Everything else is zero-config by design.

---

## 🧭 Roadmap

- [ ] Live render preview (update as you type)
- [ ] Tab support (multi-file in one window)
- [ ] Split view (vertical/horizontal)
- [ ] Minimap
- [ ] Themes (multiple built-in schemes)
- [ ] Plugin system
- [ ] LSP integration
- [ ] Git gutter

---

## 🤝 Contributing

1. Fork it
2. Create your feature branch: `git checkout -b feature/awesomeness`
3. Commit your changes: `git commit -am 'Add some awesomeness'`
4. Push to the branch: `git push origin feature/awesomeness`
5. Open a Pull Request

---

## 📜 License

MIT License

---

<div align="center">

**A small editor, honestly described.**

</div>
