# Speedready

Pacer and RSVP reader for epub/txt, built for language learners. GTK4 / libadwaita, one Python file.

- **Pacer**: the whole text on screen, a highlight sweeps through at your pace, read words dim behind it
- **RSVP**: one word (or chunk) flashed at a time with a red pivot letter
- First-run language setup; the interface and translation target follow the learner's language (English and Brazilian Portuguese UI)
- Select text in the pacer and send the phrase to DeepL or Google Translate. In beginner mode, long-press the first word and tap the last one
- Click a word to continue from there. Double-click it for a dictionary popup (lemmatized; en.wiktionary glosses plus the Duden meanings for German, browser button for the full page); close it and the flow resumes from that word
- Right-click a word you don't know: it gets a subtle underline everywhere it occurs and the pacer lingers on it. Your list lives in `unknown.txt`
- `P` reads the current sentence aloud (piper TTS, offline, voice downloaded on first use); the popup has a pronounce button
- `A` read-along: piper reads sentence by sentence and the highlight follows the voice. WPM sets the speech speed
- Chapter list from the epub's TOC (works around broken anchors by finding the headings in the text)
- Every lookup lands in `~/.config/speedready/vocab.tsv` with its sentence, importable into Anki as-is
- Remembers your position, WPM, chunk size, reading mode, beginner mode, and read-along setting per book; progress is saved atomically while you read
- Bookmarks are stored per book (`B` toggles one, `Shift+B` opens the list)
- **Library** (`L`): every book you have opened, newest first, with how far through it you are. Add several at once from the file picker, or drag epub and txt files straight onto the window. Titles come from the epub's own metadata, so the list reads like a shelf and not like a download folder
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
| B / Shift+B | toggle bookmark / open bookmarks |
| C | chapters |
| L | library |
| F11, S, O | fullscreen, settings, open |

## Dictionary packs

Beginner mode glosses each word from an offline pack, `gloss-<src>-<tgt>.sqlite`, which the app
downloads once per language pair on first use. The packs are built from English Wiktionary and each
language's own Wiktionary edition (kaikki.org), Meta's MUSE word lists, and hermitdave/FrequencyWords.

```
python tools/fetch_sources.py            # ~2 GB of extracts -> ~/.cache/speedready/build
python tools/release_packs.py --jobs 6   # build every pair, measure, keep the good ones
python tools/release_packs.py --upload   # gh release upload to the "packs" release
```

A pack is only published if it glosses at least half of the 2000 commonest words in its source
language (`--min-coverage`). Pairs below the floor are dropped rather than shipped, because a pack
that exists but glosses nothing would have the app report the dictionary ready over a page of blank
glosses. An unpublished pair is reported as such in the app.

All 90 pairs of the ten offered languages currently build and pass: median coverage 93.5%, best
es->en at 99.2%, worst ru->nl at 54.8% (Russian source words inflect further than the frequency
list and the form table between them can follow). Roughly 4.5 GB of packs, ~50 MB each.

Content words are reliable across every pair. The commonest grammar words often are not: Wiktionary
picks the wrong homograph for them (`sv->de` gives `är` as "Gut, Ware", `nl->pt` gives `is` as
"seu"). `GLOSS_OVERRIDES` in `speedready.py` fixes these by hand for de->pt only. Curating that list
once for de->en and pivoting it would fix every de->X pair at once, since knowing that `wollen` is
"want" and not "woollen" does not depend on the target language.

## Web version (any phone or browser)

`web/` is a self-contained reader for learners: the German text with a Portuguese
translation above every word you have not marked as known yet. Tap a translation to
mark the word learned and it disappears everywhere; tap a word for its dictionary entry.
It ships with a public-domain German book, speaks through the device's own voice, and
works offline once loaded (installable to the home screen).

Read-along drives the highlight from its own estimated clock rather than from
`onboundary`, which iOS reports unreliably, and re-syncs whenever a boundary event does
arrive. Devices with no speech voices installed say so instead of failing silently.

Build its data from a desktop pack:

```
python tools/export_web.py de pt      # -> web/dict-de-pt.json (8.5 MB, ~1.7 MB gzipped)
```

The shipped language pair is named in `web/bundle.json` and nowhere else; `index.html` and `sw.js`
both read it, and the reader takes its source language from the dictionary's own `src` field. So
changing which pair the website and the Android APK carry is that one command plus a starter book,
with no code edit. A test enforces it: neither file may name a dictionary or a language again.

One APK still ships one pair, because the dictionary is bundled and the app asks for no permissions
at all. Shipping more than one means either a bigger APK or network access, which is a trade worth
making deliberately.
