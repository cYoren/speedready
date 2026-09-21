#!/usr/bin/env bash
# Sets up the venv (system python + GTK bindings, plus simplemma) and installs the launcher + icon for the current user.
set -euo pipefail
cd "$(dirname "$0")"
[[ -x .venv/bin/python ]] || /usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/pip install -q simplemma piper-tts   # or: safe-install .venv/bin/pip install simplemma piper-tts
ID=io.github.cyoren.speedready
install -Dm644 icon.svg "$HOME/.local/share/icons/hicolor/scalable/apps/$ID.svg"
install -Dm644 /dev/stdin "$HOME/.local/share/applications/$ID.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Speedready
Comment=Pacer and RSVP reader for language learners
Exec=$PWD/run.sh %f
Icon=$ID
Terminal=false
Categories=Office;Education;
MimeType=application/epub+zip;text/plain;
StartupWMClass=$ID
DESK
gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
update-desktop-database -q "$HOME/.local/share/applications" 2>/dev/null || true
echo "installed: $ID  ->  run with ./run.sh or from your app launcher"
