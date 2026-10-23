# Reviewing files before publication

`AGENTS.md` is the public agent guidance for a clone of this repository. Installed
packages use their own `SKILL.md`; copying a package does not install repository
maintenance hooks. The upstream checkout additionally uses an ignored
`AGENTS.override.md` entry point and local `hook.md` maintenance workflow. Those
files are not needed by people using the skill and must not be published.

Keep real inputs, custom settings, company profiles, raw responses, account data,
customer identities and the original-to-alias mapping outside the publication set.
Use stable report-local aliases across Markdown, JSON and CSV. Evidence paths with
aliases are illustrative, not executable links to the original local evidence.
Sanitization must preserve scores, denominators, shared-session relationships,
model/provider/tool versions, reference scope and artifact hashes.

## Repeatable checks

Use a development Python environment with `requirements-dev.txt` installed:

```text
python tools/publication_check.py worktree
python tools/publication_check.py index
python tools/publication_check.py history --refs main
python tools/publication_check.py history --refs v0.3.17
python tools/publication_check.py artifact --artifacts PACKAGE.zip SHA256SUMS.txt RELEASE-NOTES.md
```

The index command reads exact staged blobs and the staged review manifest. Stage
only reviewed files; repeat after every index change. History scans every unique
path/blob pair reachable from the supplied refs (or an explicitly supplied range),
including intermediate commits and commit/tag messages. Before making a private
repository public, enumerate **all remote branches and tags** and scan their full
history. A clean latest commit or outgoing range does not clean older history.
Recognized public noreply addresses are accepted only in Git attribution lines;
addresses in report text or unrelated commit-message prose remain subject to review.

Inspect actual final release assets, release notes and GitHub's automatic source
ZIP/tar.gz downloads. Source archives follow tags, not the latest branch. Check
checksums and compare archive contents to the reviewed snapshot. A clean package
asset does not establish that its source archive is clean.

The checker scans every text extension, decoded paths, filenames, archive members,
spreadsheet XML and PDF text/metadata. Unknown binaries, failed decoding,
encrypted/unreviewed PDFs and inspection limits block the check. Render PDFs and
inspect all pages, attachments and metadata before approving their exact SHA-256
in `publication-review.json`; inspect other binary formats manually as needed.
Changed bytes invalidate that approval. A fingerprint records an artifact review,
not a disguised private identifier. Never approve a private document merely to
make the check pass.

`synthetic_matches` permits only individually reviewed literal examples, keyed by
file, location, category and value with a reason. It cannot exempt a directory or
an entire report. Review changes to this manifest just like source changes; never
add actual private values as exceptions. Findings show location/category rather
than the matched value. Review filenames and descriptions manually too: private
names and unfamiliar identifier formats cannot all be recognized by patterns.

## Optional local Git guards

```text
python tools/install_publication_hooks.py
```

Installation is explicit for each clone. The installer refuses to replace existing
hooks or a configured hooks directory. Pre-commit checks the exact index;
pre-push checks the complete history reachable from every proposed ref. Hooks
use the Python interpreter used at installation, whose path stays only in local
Git metadata. Reinstall deliberately if that environment is removed.

Hooks do not run automatically on GitHub visibility changes, web uploads or other
clones, and can be bypassed. They supplement owner approval and final manual
review; they cannot guarantee that all private information is detected. Do not
push internal application refs with a mirror push.

## Snapshot publication

This repository has independent Git history, starting from a reviewed source snapshot.
Imported evaluation reports retain their original scores, reference scope and hashes.
They are historical evidence, not new measurements of this repository snapshot.
Private source documents, runs and alias mappings are excluded. Do not merge history
from an older checkout into this repository; use a fresh clone and reviewed changes.
