"""glossOf must prefer a word's own entry over a redirect through the form table.

Spanish 'pueblo' is a village and also a form of 'poblar' (to populate); 'invierno' is a
winter and also a form of 'invernar' (to hibernate). When the form table was consulted
first, both were glossed as the verb. German depends on the same rule for the opposite
reason: 'Forscher' is the noun, not a form of 'forschen'.

Runs the real function lifted out of web/index.html under node; skipped without node.
"""
import json, re, shutil, subprocess, tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

# A dictionary shaped like the packs the reader downloads: g = glosses, f = form -> lemma.
DICT = {
    "src": "es", "tgt": "en",
    "o": {},
    "g": {
        "invierno": "winter", "pueblo": "village, town",
        "invernar": "to hibernate", "poblar": "populate, inhabit",
        "Forscher": "explorer", "forschen": "to research",
        "Haus": "house", "hausen": "to live in squalor",
    },
    "f": {
        "invierno": "invernar", "pueblo": "poblar",
        "Forscher": "forschen", "haus": "hausen",
    },
    "s": {},
}

CASES = [
    ("invierno", "winter", "a form of 'invernar' must not win over the noun"),
    ("pueblo", "village, town", "a form of 'poblar' must not win over the noun"),
    ("Forscher", "explorer", "German capitalisation keeps the noun"),
    ("invernar", "to hibernate", "a word that is only a lemma still resolves"),
]

RUN = """
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const dict = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const m = src.match(/function glossOf\\(word\\)\\{[\\s\\S]*?\\n\\}/);
if (!m) { console.error('glossOf not found in index.html'); process.exit(2); }
const strip = w => w.replace(/^[^\\p{L}\\p{N}]+|[^\\p{L}\\p{N}]+$/gu, '');
const S = { dict, book: null, native: 'en' };
const glossOf = new Function('S', 'strip', m[0] + '; return glossOf;')(S, strip);
const out = {};
for (const w of JSON.parse(process.argv[4])) out[w] = glossOf(w)[0];
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_word_entry_beats_form_table():
    with tempfile.TemporaryDirectory() as d:
        script = Path(d) / "run.js"
        script.write_text(RUN)
        data = Path(d) / "dict.json"
        data.write_text(json.dumps(DICT))
        words = [w for w, _, _ in CASES]
        out = json.loads(
            subprocess.run(
                [NODE, str(script), str(ROOT / "web" / "index.html"), str(data), json.dumps(words)],
                check=True, capture_output=True, text=True,
            ).stdout
        )
    for word, expected, why in CASES:
        assert out[word] == expected, f"{word}: got {out[word]!r}, wanted {expected!r} ({why})"
