# Portable HTML workflow implementation plan

> Execute inline with superpowers:executing-plans. User authorized fixes, commit and push to the original repository.

Goal: keep existing ccudj and legacy commands usable while separating tools, question banks and course data.

Constraints:
- Preserve existing command names and positional arguments.
- Accept problem.html, problem.pdf and problem.txt.
- Explicit --env / CCUDJ_ENV_FILE; resolve file-configured relative data/output paths against the env file, command-line paths against cwd.
- Optional OUTPUT_DIR, defaulting to DATA_DIR; individual roster imports and setup must agree.
- Problem identifiers/paths and human titles are separate; support --title and --output-dir for new problems.
- Package only documented problem files and standard package directories; omit local secrets, authoring outputs and symlinks.
- --validate-only requires no credentials, network or ZIP output.
- Upload stays on the global, no-contest endpoint. No live course or problem updates during tests.
- Do not commit local question banks, student data, credentials, executables or earlier authoring plans.

Tasks:
- [x] Confirm remote and run clean baseline (47 passing tests).
- [x] Add failing regression tests for HTML, naming, packaging, config and external-directory commands.
- [x] Implement config/CLI and compatible roster output routing.
- [x] Implement generator and uploader portability and run full tests.
- [x] Update bilingual docs and examples.
- [x] Obtain independent code review, fix findings and rerun affected/full checks.
- [ ] Commit only tool files, fast-forward main, test merged source and push normally to origin/main.

Review focus: env precedence and no cross-call leakage; independently located source/output; base paths and names with spaces; packaging destination inside input; validation-only without server access; legacy wrappers.

Validation: 71 tests pass. Independent review found and verified fixes for named env files, native build artifacts, and counting excluded data pairs. The three existing HTML problem packages validate from an unrelated working directory, and rebuilt archives match all 46 original entries per problem. Installed ccudj launcher also creates a titled problem in a separately located directory.
