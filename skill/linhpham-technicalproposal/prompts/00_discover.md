# Phase 0 — Discover the project folder

The user invoked `/linhpham-technicalproposal <projectname>`. Find a folder whose
name fuzzy-matches `<projectname>` and contains input files.

## Search strategy

Do **NOT** hard-code customer-, bid-, or user-specific paths. Discover dynamically:

1. **Current working directory** — first check if `./` itself matches `<projectname>`.
2. **Ancestors of CWD** — walk up the directory tree (max 5 levels); at each level
   scan immediate children for a match.
3. **Standard project roots that exist on this machine** — for each candidate root
   below, skip silently if it does not exist; otherwise scan its immediate children
   and one level deeper:
   - `~/Projects`, `~/projects`, `~/Documents/Projects`
   - `~/workspace`, `~/repos`, `~/src`, `~/code`
   - On Windows only: `<drive>:\Projects` for every fixed drive letter present
     (enumerate via `Get-PSDrive -PSProvider FileSystem` or `wmic logicaldisk`).
4. **Sub-roots** — if any of the roots above contain a sub-folder whose name reads
   like a grouping (`Inquiry`, `Inquiries`, `Bid`, `Bids`, `AI`, `Private`, `Study`,
   `Clients`, `Customers`), descend one extra level into it.

The goal is to locate the project regardless of where the user keeps it, without
baking specific customer or bid folder names into the prompt.

## Match logic

A candidate folder qualifies if **all** are true:

- Folder name **case-insensitively** matches `<projectname>` exactly,
  OR matches after normalising (strip `-`, `_`, spaces, lowercase both sides),
  OR the normalised projectname is a substring of the normalised folder name (and
  vice-versa) — accept fuzzy hits and let the disambiguation step below handle ties.
- Folder contains at least one file with a supported extension:
  `.pdf` `.docx` `.doc` `.txt` `.md` `.xlsx` `.xls` `.pptx` `.csv`
  `.png` `.jpg` `.jpeg` `.webp`
  (search **up to 5 levels deep** — clients often nest docs in
  sub-folders like `requirements/`, `references/`, `screenshots/`).
- Skip artefacts when counting input files: Word lock files (`~$*`),
  macOS `.DS_Store`, Windows `Thumbs.db` / `desktop.ini`, hidden files
  (`.*`), and the skill's own `output/` folder if present.
- Folder is not the skill's own folder or any directory under it.

If multiple candidates qualify, use AskUserQuestion to disambiguate
(list each candidate with absolute path + file count).

If no candidate qualifies, output a clear error listing:

- the projectname tried,
- the search roots scanned,
- the closest folder-name matches found (even if they had no input files),
- and stop. Do not invent a project.

## Output of this phase

Set the variable `project_dir` (absolute path) for use in later phases.
List the input files found, grouped by extension, with sizes.
