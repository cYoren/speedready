# Submitting to the stores

Both stores expect the author to submit, not an automated agent. Flathub says so
explicitly. Everything technical is ready; these are the steps only you can take.

## Flathub

The branch is already pushed to your fork, so this is a form, not a git exercise.

1. Open https://github.com/cYoren/flathub/pull/new/io.github.cyoren.speedready
2. Set the **base branch** to `new-pr` (not `master`)
3. Paste `flathub-pr-body.md` as the description and complete the checklist honestly
4. Attach a short screen recording of the installed Flatpak

The branch already carries the manifest pinned to tag `v1.0.1`, which builds and passes
`flatpak-builder-lint` locally. Nothing else to prepare.

Before you do, read their development-history requirement. A repository that is days old,
with no users yet, is the thing they most often turn down:
https://docs.flathub.org/docs/for-app-authors/requirements#insufficient-development-history

To record the video, install the local build and capture a minute of reading:

```
flatpak run io.github.cyoren.speedready
```

## F-Droid

Submitted: https://gitlab.com/fdroid/fdroiddata/-/merge_requests/49884

Their server does exactly what was verified here: clone the repo at tag `v1.0.1`, run
`gradle assembleRelease` in `android/app`, and sign the result with its own key. The
metadata passes `fdroid lint` and `fdroid readmeta`.

Watch the merge request for review comments; the queue is measured in weeks.
