Status: current (2026-11-26)

# Release decisions still open

Speedready 1.0.10 is tagged, signed, published, and reproducibly verified by
F-Droid. The completed build and signing evidence lives in the git history and
the release tag, not in this file.

Only these owner-dependent actions remain:

## F-Droid fork

The F-Droid metadata and merge-request text are prepared in
`packaging/submission/`. Push the metadata to the `speedready` branch of the
fork and update the existing merge request. The exact commands are in
[`packaging/submission/README.md`](packaging/submission/README.md).

## Play production

Upload the 1.0.10 bundle to the production track. This is a real-user release,
so it needs an explicit go-ahead and a `gradle bundleRelease` artifact rather
than the already-verified APK.

```bash
gplay release --package io.github.cyoren.speedready --track production --bundle <1.0.10>.aab
```

## Bundled language pairs

Choose the next APK bundle policy in
[`docs/bundle-decision.md`](docs/bundle-decision.md): keep the current single
pair, add the two recommended pairs, or download every pair on first use.

## iOS

The iOS app needs the equivalent 1.0.10 release and a Mac signing pass. This
cannot be completed from this workstation.
