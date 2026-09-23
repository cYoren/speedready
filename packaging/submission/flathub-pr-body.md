<!-- Paste this as the body when opening the PR yourself, then tick each box you can
     honestly tick. The three marked << YOU >> only you can answer. -->

### Please confirm your submission meets all the criteria

- [x] Please describe the application briefly.

  Speedready is a reader for people learning a language. It paces you through an EPUB so
  you keep reading instead of stopping at every unfamiliar word, and puts the dictionary
  where your eyes already are: above each word you have not marked as learned sits its
  translation in your own language, and clicking that translation removes it from the whole
  book. It also marks words you are still learning, reads sentences aloud, and exports
  everything you looked up to Anki. Dictionaries and voices are downloaded once and then
  work offline. Upstream: https://github.com/cYoren/speedready

- [ ] Please attach a video showcasing the application on Linux using the Flatpak.
  << YOU: record a short screen capture of the installed Flatpak and attach it here >>

- [x] The Flatpak ID follows all the rules listed in the Application ID requirements.

  `io.github.cyoren.speedready` matches https://github.com/cYoren/speedready

- [ ] I have read and followed all the Submission requirements and the Submission guide and I agree to them.
  - [ ] The application has a meaningful development history, evidence of real-world use, and a clear commitment to ongoing maintenance.
    << YOU: the repository is new. Read their development-history requirement before
       ticking this; it may be worth letting the project run for a while first. >>
  - [x] I have disclosed any AI-generated material included in the application or its
        Flathub packaging. **Affected parts and approximate extent:**

    Most of the source code, the Flatpak packaging and the metadata in this submission were
    written by an AI assistant working from my direction, over an extended session.
    I reviewed and directed the work, tested the application, and I maintain it. The offline
    dictionary is built from Wiktionary, MUSE and a frequency list by a script in the
    repository; the bundled starter text is public domain from Project Gutenberg.

  - [ ] I have not used AI tools or agents to generate or automate this submission pull
        request or its review interactions.
    << YOU: only tick this if you open the PR and handle the review yourself. >>

- [ ] I am an author/developer/upstream contributor to the project.
