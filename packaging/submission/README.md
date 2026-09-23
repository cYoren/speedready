# Submitting to the stores

Both stores expect the author to submit, not an automated agent. Flathub says so
explicitly. Everything technical is ready; these are the steps only you can take.

## Flathub

The branch is already pushed to your fork, so this is a form, not a git exercise.

1. Open https://github.com/cYoren/flathub/pull/new/io.github.cyoren.speedready
2. Set the **base branch** to `new-pr` (not `master`)
3. Paste `flathub-pr-body.md` as the description and complete the checklist honestly
4. Attach a short screen recording of the installed Flatpak

Before you do, read their development-history requirement. A repository that is days old,
with no users yet, is the thing they most often turn down:
https://docs.flathub.org/docs/for-app-authors/requirements#insufficient-development-history

To record the video, install the local build and capture a minute of reading:

```
flatpak run io.github.cyoren.speedready
```

## F-Droid

F-Droid lives on GitLab, so it needs a GitLab account.

1. Fork https://gitlab.com/fdroid/fdroiddata
2. Add `android/fdroid/io.github.cyoren.speedready.yml` from this repository as
   `metadata/io.github.cyoren.speedready.yml` in your fork
3. Open a merge request against `fdroiddata` titled `New app: Speedready`

Their server does exactly what was verified locally: clone the repo at tag `v1.0.0`, run
`gradle assembleRelease` in `android/app`, and sign the result with its own key.

If you would rather have them package it, open a request instead at
https://gitlab.com/fdroid/rfp/-/issues/new and link the repository.
