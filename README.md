# Speedready

Pacer and RSVP reader for epub/txt, built for language learners. GTK4 / libadwaita, one Python file.

- **Pacer**: the whole text on screen, a highlight sweeps through at your pace, read words dim behind it
- **RSVP**: one word (or chunk) flashed at a time with a red pivot letter
- Click a word to continue from there. Double-click it for a dictionary popup (lemmatized; en.wiktionary glosses plus the Duden meanings for German, browser button for the full page); close it and the flow resumes from that word
- Right-click a word you don't know: it gets a subtle underline everywhere it occurs and the pacer lingers on it. Your list lives in `unknown.txt`
- `P` reads the current sentence aloud (piper TTS, offline, voice downloaded on first use); the popup has a pronounce button
- `A` read-along: piper reads sentence by sentence and the highlight follows the voice. WPM sets the speech speed
- Chapter list from the epub's TOC (works around broken anchors by finding the headings in the text)
- Every lookup lands in `~/.config/speedready/vocab.tsv` with its sentence, importable into Anki as-is
- Remembers your position per book and reopens the last book
- Everything is configurable in the settings dialog (fonts, colours, pauses, chunk size, dictionaries)

## Install (Linux, GTK4 + libadwaita + python-gobject)

```
./install.sh        # venv with simplemma + piper-tts, launcher + icon
./run.sh book.epub  # or open "Speedready" from your app launcher
```

## Keys

| key | action |
|---|---|
| space | play / pause |
| ← → | ±10 words |
| PageUp / PageDown | ±one page |
| ↑ ↓ | speed ±5 (shift: ±25) |
| [ ] | words per step |
| M | pacer / rsvp |
| R | replay sentence |
| D | define current word |
| click / double-click / right-click | continue from there / dictionary popup / mark unknown |
| P | speak from here to the end of the sentence, again to stop |
| A | read-along |
| C | chapters |
| F11, S, O | fullscreen, settings, open |
