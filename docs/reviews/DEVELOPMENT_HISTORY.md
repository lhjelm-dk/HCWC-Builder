# Development history: where the dated decisions live

Until 21 September 2026 the production code carried about a hundred dated attributions
("Lars, 4 Sep 2026: …", "the honest fix", "until it was caught on 27 Aug") in comments and
docstrings. The final review (`docs/FINAL_AUDIT_2026-09.md`, brief W) moved the who-and-when out of
the source and kept the explanation where it explains a calculation. The record is:

- **git history**: every commit message from 25 August 2026 names the decision and the date; `git
  log -S"<phrase>"` finds the commit that introduced or removed a sentence.
- **`docs/reviews/`**: the five review documents and this file.
- **`docs/AUDIT_2026-09-14.md`, `docs/DHI_AUDIT_2026-09-16.md`**: the two numerical audits, with
  the defects they found and fixed.
- **`archive/development_notes/`**: the signed working note of 25 August (`DHI_alignment.md`), the
  explanation map of 16 September, the interfacial-tension check of 15 September.
- **`archive/superseded_notes/`**: the essays 8.1 replaced, and the first article draft.
- **`docs/REFACTOR_VALIDATION.md`**: what the clean-up of 18–20 September moved and changed.

Sentences of the form "Until <date> this read …" that remain in the code explain a calculation
by contrast with its predecessor and stay for that reason.
