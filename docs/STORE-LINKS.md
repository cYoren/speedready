# Where Speedready is sold, and what is still "soon"

| Store | Status | URL |
|---|---|---|
| Google Play (Android) | live | https://play.google.com/store/apps/details?id=io.github.cyoren.speedready |
| App Store (iPhone, iPad) | live | https://apps.apple.com/app/id6818031802 |
| Chrome Web Store | live | item `hbhcnalebmhlheopbailoeeomlpcaiki` |
| Firefox Add-ons | live | slug `speedready-speed-reader-for-pa`, id `speedready@cyoren.github.io` |
| Safari (inside the iOS app) | built, needs the Mac | `dist/safari` from `tools/build_chrome.py` |
| Microsoft Store | not submitted | — |

## The rule when a store goes live

Change these in one commit, so the funnel never points at a dead page:

1. `store/chrome/listing.md`, the `ALSO FROM US` / `TAMBÉM NOSSO` lines.
2. The popup footer (`chrome/popup.html`, `#phone`) and its `phoneApp` string in every
   `chrome/_locales/*/messages.json`.
3. This table.

## Why it matters

The extension is free and the app is the paid product, so the extension is the top of the
funnel. The listing and the popup are the only two places a reader of a web page learns the app
exists; both should name the stores directly rather than send people to a hub page that then
asks them to pick a platform.
