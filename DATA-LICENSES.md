## Dictionary data licences

The reader application code is licensed under the MIT License in `LICENSE`. Dictionary data is separate from the application code and retains the terms of its upstream sources:

- Wiktionary content and derived dictionary entries: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0). Source: [Wiktionary:Copyrights](https://en.wiktionary.org/wiki/Wiktionary:Copyrights). The pack builder uses Wiktionary extracts served by [kaikki.org](https://kaikki.org/).
- Frequency lists: [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords), MIT License. Copyright 2016 Hermit Dave. Its `LICENSE` is included in the upstream repository.
- Starter book `Japanische Märchen`: public domain; sourced from [Project Gutenberg](https://www.gutenberg.org/).

The non-commercial MUSE dictionaries are not used or distributed by this release. The online source files may remain in a developer's local cache, but the build scripts do not read, package, or publish them.

## Book catalog and language names

- `web/catalog.json.gz` is a compact snapshot of [Project Gutenberg's official machine-readable catalog](https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv). Gutenberg grants its catalog metadata to the public domain; see [catalog access policy](https://www.gutenberg.org/policy/robot_access.html#how-to-get-catalog-data). Individual downloaded books retain their own terms and license notices.
- `web/languages.json` contains ISO 639 language names and code aliases derived from the system `iso-codes` data, with a bundled license at `web/LICENSE.iso-codes.txt`, released under [LGPL 2.1 or later](https://salsa.debian.org/iso-codes-team/iso-codes/-/blob/main/COPYING).
