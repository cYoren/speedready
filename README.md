# Speedready

Pacer and RSVP reader for epub/txt, built for language learners. GTK4 / libadwaita, one Python file.

- **Pacer**: the whole text on screen, a highlight sweeps through at your pace, read words dim behind it
- **RSVP**: one word (or chunk) flashed at a time with a red pivot letter
- Click any word: you jump there and get a dictionary popup (lemmatized, en + de Wiktionary, Duden button for German). Close it and the flow resumes from that word
- Every lookup lands in `~/.config/speedready/vocab.tsv` with its sentence, importable into Anki as-is
- Remembers your position per book and reopens the last book
- Everything is configurable in the settings dialog (fonts, colours, pauses, chunk size, dictionaries)

## Install (Linux, GTK4 + libadwaita + python-gobject)

```
./install.sh        # venv with simplemma, launcher + icon
./run.sh book.epub  # or open "Speedready" from your app launcher
```

## Keys

| key | action |
|---|---|
| space | play / pause |
| ← → | ±10 words |
| PageUp / PageDown | ±one page |
| ↑ ↓ | speed |
| [ ] | words per step |
| M | pacer / rsvp |
| R | replay sentence |
| D | define current word |
| click / ctrl+click | go there + dictionary / just go there |
| F11, S, O | fullscreen, settings, open |
