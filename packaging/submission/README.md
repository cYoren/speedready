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

Their server does exactly what was verified here: clone the repo at the commit the build entry
names, run `gradle assembleRelease` in `android/app`, and sign the result with its own key. The
metadata passes `fdroid lint` and `fdroid readmeta`, and `fdroid build` from a checkout of that
commit produces the same unsigned APK the signed release contains, which is what their
reproducible-build check compares.

### What is left: two edits on GitLab, no code

The fork branch `speedready` in `gustavo.cesar.marcelino4/fdroiddata` still carries the `1.0.7`
build entry, and the merge request description still describes the old release. Both are prepared
in this repository:

- **Description.** Paste `fdroid-mr-body.md` over the merge request body
  (Edit → replace the whole description → Save).
- **Metadata.** `../android/fdroid/io.github.cyoren.speedready.yml` is the file to copy over
  `metadata/io.github.cyoren.speedready.yml` on the `speedready` branch. It names `v1.0.9`: version
  name, version code, full commit hash, the same `AllowedAPKSigningKeys`, and the `scanignore`
  entries F-Droid's scanner needs for every `.gz` under `web/`.

There is no credential for GitLab on this workstation (no `glab`, no token, and the SSH key is not
in a GitLab account), which is why this last push is yours:

```
git clone -b speedready https://gitlab.com/gustavo.cesar.marcelino4/fdroiddata
cd fdroiddata
cp ~/Projects/speedready/android/fdroid/io.github.cyoren.speedready.yml metadata/
git commit -am "io.github.cyoren.speedready: 1.0.9"
git push          # asks for your GitLab username + a personal access token as the password
```

A working copy with that commit already staged is at
`~/.cache/speedready/fdroiddata-fork/repo` if you would rather just `git push` from there.

Before pushing, `python tools/check_release_tag.py --strict v1.0.9` in this repository must print
ok: it compares the metadata's version, code and commit against the tag.

Watch the merge request for review comments; the queue is measured in weeks.
