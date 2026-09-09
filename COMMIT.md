# Commit on this checkout

Policy (agreement, message, `eng_verify`, `ARCHITECTURE.md`) is `eng/AGENTS.md` **Git discipline**. This file is **how to invoke git** when that policy meets this machine.

Do not invent a second policy here.

---

## Current condition

The working copy is a **Windows folder** (OneDrive) opened from **WSL** (`/mnt/c/Users/...`).

| Probe | Typical result here |
|------|---------------------|
| WSL `git add` / `git commit` | Fails: cannot create `.git/index.lock` (`.git` shows `root:root` `755`) |
| WSL `git status` | May list **thousands** of files (`+x` on NTFS, CRLF). Slow. `dubious ownership` |
| Git for Windows `git.exe` | Status is the real increment. `index.lock` works |
| `sudo chown` on `/mnt/c/.../.git` | Often does not stick. Not the fix |
| New file under `eng/` | May fail (`eng/` is `root:root` `755`). Editing an existing `eng/` file can still work. This file lives at repo root for that reason |

`/smart-commit` is still agreement to commit. Push, amend, and force still need a separate ask.

If the checkout later lives on a Linux disk (`~/...`), re-run the probes. Use WSL `git` when `touch .git/index.lock` works. Do not keep `git.exe` out of habit.

---

## 1. Pick a git that can write

Stop at the first probe that works.

```bash
# A — Git for Windows (usual winner on this checkout)
GIT="/mnt/c/Program Files/Git/cmd/git.exe"
REPO="C:/Users/user/OneDrive/Documents/Stock Research"
"$GIT" -C "$REPO" status -sb

# B — WSL git, only if the lock file can be created
touch .git/index.lock && rm -f .git/index.lock && git status -sb
```

If A works and B cannot create `.git/index.lock`, **add and commit with A**. WSL `git diff` is fine for reading one path; do not trust a WSL dirty list of the whole tree.

---

## 2. See the real increment

When WSL status is huge:

```bash
"$GIT" -C "$REPO" status -sb
# or, from WSL:
git -c safe.directory="$PWD" diff --ignore-cr-at-eol --stat HEAD
```

Stage **only** paths with a real content diff, plus new work-product files.

**Do not `git add -A`.** That would commit `+x` / CRLF on thousands of files.

If a file you edited is CRLF on disk and LF at HEAD, convert it to LF before add so the commit is the edit, not line endings.

New files: `git add --chmod=-x -- <path>` so they land `100644`, not `100755`.

---

## 3. Verify, then commit

Use a Python that has pytest and UTF-8. On this machine that is often Windows Python 3.12, not WSL `python3`.

```bash
python3 -c "import pytest"
"/mnt/c/Users/user/AppData/Local/Programs/Python/Python312/python.exe" -c "import pytest; print('ok')"
```

If Windows Python is the one that works, run verify with UTF-8 (cmd.exe):

```bat
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe scripts\eng_verify.py
```

After **user agreement** (`commit`, `/smart-commit`, …):

```bash
"$GIT" -C "$REPO" add --chmod=-x -- <paths>
"$GIT" -C "$REPO" commit -m "<what changed + why>"
"$GIT" -C "$REPO" status -sb
"$GIT" -C "$REPO" log -1 --stat
```

Do not push unless asked.

---

## Do not

- `git add -A` while WSL status is the whole tree
- Commit `tmp/**`, secrets, or a stale `ARCHITECTURE.md`
- Rewrite `archive/research/**` or `archive/outcomes/**` to green tests
- Treat “WSL git is dirty” as “the increment is 2600 files”
