#!/usr/bin/env bash
# One-command installer for AI Workflow Studio (macOS / Linux).
#
#   curl -fsSL https://raw.githubusercontent.com/linhphamSTS/AI-Workflow-Studio/main/get.sh | bash
#
# Downloads the repo, makes sure a Python is available (fetching one through uv if the
# machine has none), sets up the web app, deploys every skill into every Claude Code
# profile, offers to install the Claude Code CLI if it is missing, checks whether you are
# signed in, adds an `aiws` command, and starts the app.
#
# Signing in is the one step that cannot be automated: it opens a browser. If you are not
# signed in, the installer says so and tells you the command to run.
#
# Nothing needs sudo and nothing is installed system-wide.
#
# Options (when piping, pass them after `bash -s --`):
#   --yes        do not ask anything; accept the Claude Code CLI install
#   --no-start   set everything up but do not launch the app
#   --dir PATH   where to install (default ~/.local/share/ai-workflow-studio)
#
#   curl -fsSL .../get.sh | bash -s -- --yes --no-start
#
# Equivalent environment variables: AIWS_YES=1  AIWS_NO_START=1  AIWS_DIR=...

set -euo pipefail

REPO="linhphamSTS/AI-Workflow-Studio"
BRANCH="main"
APP_NAME="AI Workflow Studio"

ASSUME_YES="${AIWS_YES:-}"
NO_START="${AIWS_NO_START:-}"
HERE_MODE="${AIWS_HERE:-}"
DIR="${AIWS_DIR:-$HOME/.local/share/ai-workflow-studio}"
BIN_DIR="$HOME/.local/bin"

while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y)   ASSUME_YES=1 ;;
    --no-start) NO_START=1 ;;
    --here)     HERE_MODE=1 ;;
    --dir)      DIR="${2:?--dir needs a path}"; shift ;;
    -h|--help)  sed -n '2,26p' "$0" 2>/dev/null || echo "See the header of get.sh"; exit 0 ;;
    *)          echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

if [ -t 1 ]; then
  C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
  C_RED=$'\033[31m'; C_GRAY=$'\033[90m'; C_OFF=$'\033[0m'
else
  C_CYAN=''; C_GREEN=''; C_YELLOW=''; C_RED=''; C_GRAY=''; C_OFF=''
fi

STEP=0
step() { STEP=$((STEP + 1)); printf '\n%s[%d] %s%s\n' "$C_CYAN" "$STEP" "$1" "$C_OFF"; }
ok()   { printf '    %s%s%s\n' "$C_GREEN"  "$1" "$C_OFF"; }
info() { printf '    %s%s%s\n' "$C_GRAY"   "$1" "$C_OFF"; }
warn() { printf '    %s%s%s\n' "$C_YELLOW" "$1" "$C_OFF"; }
fail() { printf '\n  %sInstall failed: %s%s\n\n' "$C_RED" "$1" "$C_OFF" >&2; exit 1; }

confirm() {
  [ -n "$ASSUME_YES" ] && return 0
  # When this script arrives through a pipe, stdin IS the script, so a prompt has to read
  # the terminal directly. With no terminal at all (CI) the safe answer is no.
  if [ ! -r /dev/tty ]; then
    info "Non-interactive session, assuming no. Re-run with --yes to accept."
    return 1
  fi
  local a
  while true; do
    printf '    %s [Y/n] ' "$1" > /dev/tty
    read -r a < /dev/tty || return 1
    case "$(printf '%s' "$a" | tr '[:upper:]' '[:lower:]')" in
      ''|y|yes) return 0 ;;
      n|no)     return 1 ;;
    esac
  done
}

need() { command -v "$1" >/dev/null 2>&1; }

printf '\n  %s\n' "$APP_NAME"
printf '  %sSA-grade deliverables, from a prompt%s\n' "$C_GRAY" "$C_OFF"
printf '  %sInstalling into %s%s\n' "$C_GRAY" "$DIR" "$C_OFF"

# --here treats the folder this script sits in AS the install and skips the download. For a
# developer working in a clone: wires up the aiws command and the desktop entry without
# mirroring GitHub over the work in progress.
if [ -n "$HERE_MODE" ]; then
  case "$0" in
    /*) DIR="$(cd "$(dirname "$0")" && pwd)" ;;
    *)  fail "--here needs this script saved to disk (it cannot work from a pipe). Use --dir." ;;
  esac
fi

# ------------------------------------------------------------------ 1. get the code
if [ -n "$HERE_MODE" ]; then
step "Using the code already in this folder"
[ -f "$DIR/install.py" ] || fail "$DIR does not look like the repo (no install.py)."
ok "Skipping the download."
else
step "Downloading the repository"
need curl || fail "curl is required and was not found."
need tar  || fail "tar is required and was not found."

# Record which commit this install came from, so `aiws update` can tell whether there is
# anything to do without downloading 65 MB to find out.
HEAD_SHA="$(curl -fsSL -H 'Accept: application/vnd.github.sha' -H 'User-Agent: aiws-installer' \
  "https://api.github.com/repos/$REPO/commits/$BRANCH" 2>/dev/null || true)"

IS_UPDATE=""
[ -f "$DIR/install.py" ] && IS_UPDATE=1

STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

info "About 65 MB, so this is the slow step."
curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" -o "$STAGING/repo.tar.gz" \
  || fail "could not download the repository."
mkdir -p "$STAGING/src"
tar -xzf "$STAGING/repo.tar.gz" -C "$STAGING/src" --strip-components=1 \
  || fail "could not unpack the archive."
[ -f "$STAGING/src/install.py" ] || fail "the archive did not contain what was expected."

if [ -n "$IS_UPDATE" ]; then
  info "Existing install found, updating it and leaving your workspaces alone."
  # --delete removes anything the archive does not contain, so everything the USER owns has
  # to be named here. .git matters most: a GitHub archive has no .git, so installing over a
  # CLONE would otherwise delete its entire history. Workspaces hold generated work that
  # exists nowhere else, and .venv is expensive to rebuild.
  if need rsync; then
    rsync -a --delete \
      --exclude '/.git/' --exclude '/webapp/workspaces/' --exclude '/webapp/.venv/' \
      "$STAGING/src/" "$DIR/" || fail "syncing the new files failed."
  else
    info "rsync not found, copying over the top instead (stale files may remain)."
    rm -rf "$STAGING/src/webapp/workspaces" "$STAGING/src/webapp/.venv"
    cp -R "$STAGING/src/." "$DIR/" || fail "copying the new files failed."
  fi
  ok "Updated."
else
  mkdir -p "$DIR"
  cp -R "$STAGING/src/." "$DIR/" || fail "copying the files failed."
  ok "Downloaded."
fi
if [ -n "$HEAD_SHA" ]; then
  printf '{"sha": "%s", "branch": "%s", "installed": "%s"}\n' \
    "$HEAD_SHA" "$BRANCH" "$(date -u +%Y-%m-%dT%H:%M:%S)" > "$DIR/.aiws-version"
fi
fi   # end of the download branch skipped by --here
chmod +x "$DIR"/*.sh "$DIR"/webapp/*.sh "$DIR"/*/deploy.sh "$DIR"/*/deploy.command 2>/dev/null || true

# ------------------------------------------------------------------ 2. a working Python
step "Looking for Python 3.10 or newer"

PY=""
py_ok() { "$1" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,10) else 1)' >/dev/null 2>&1; }
for cand in python3 python; do
  if need "$cand" && py_ok "$cand"; then
    PY="$(command -v "$cand")"
    ok "Found $("$PY" -c 'import sys; print("Python %d.%d" % sys.version_info[:2])') ($cand)"
    break
  fi
done

if [ -z "$PY" ]; then
  info "No suitable Python on this machine. Fetching a private one with uv."
  info "It lives in uv's own directory and does not become your system Python."
  if ! need uv; then
    info "Installing uv (a single binary, no sudo needed) ..."
    curl -LsSf https://astral.sh/uv/install.sh | sh || fail "could not install uv."
    export PATH="$HOME/.local/bin:$PATH"
  fi
  need uv || fail "uv installed but is not on PATH. Open a new terminal and run this again."
  uv python install 3.12 || fail "uv could not install Python 3.12."
  PY="$(uv python find 3.12 2>/dev/null | head -n1)"
  [ -n "$PY" ] && [ -x "$PY" ] || fail "uv installed Python but its path could not be resolved."
  ok "Using $PY"
fi

# ------------------------------------------------------------------ 3. skills + web app
step "Deploying the skills and setting up the web app"
info "Creates a private virtual-env, installs dependencies, and ensures Graphviz."
( cd "$DIR" && "$PY" install.py ) || warn "install.py reported warnings, see the output above."

# ------------------------------------------------------------------ 4. the Claude Code CLI
step "Checking the Claude Code CLI"

if ! need claude; then
  warn "Not installed. The skills and the web app both drive it, so it is required."
  if confirm "Install Claude Code now (from claude.ai, no sudo)?"; then
    curl -fsSL https://claude.ai/install.sh | bash || warn "Automatic install failed."
    export PATH="$HOME/.local/bin:$PATH"
    need claude && ok "Installed."
  else
    info "Skipped. Install it later: curl -fsSL https://claude.ai/install.sh | bash"
  fi
fi

SIGNED_IN=""
if need claude; then
  if claude auth status --json 2>/dev/null | grep -q '"loggedIn"[[:space:]]*:[[:space:]]*true'; then
    SIGNED_IN=1
    ok "Signed in."
  else
    warn "Installed but NOT signed in."
  fi
fi

# ------------------------------------------------------------------ 5. the aiws command
step "Adding the aiws command"

mkdir -p "$BIN_DIR"
# The interpreter is pinned rather than looked up at run time: when uv supplied the Python it
# is deliberately not on PATH, so a launcher that searched for one would find nothing. Prefer
# the virtual-env interpreter step 3 just built, which is one exact absolute Python; fall back
# to the bootstrap one only if that step did not get there.
RUN_PY="$DIR/webapp/.venv/bin/python"
[ -x "$RUN_PY" ] || RUN_PY="$PY"
# Calls tools/aiws.py rather than launch.py directly: that is where `aiws update`, the version
# report and the pre-start update check live, shared with the Windows launcher.
cat > "$BIN_DIR/aiws" <<EOF
#!/usr/bin/env bash
# Start $APP_NAME. Generated by get.sh - re-run the installer to regenerate.
exec "$RUN_PY" "$DIR/tools/aiws.py" "\$@"
EOF
chmod +x "$BIN_DIR/aiws"

case ":$PATH:" in
  *":$BIN_DIR:"*) ok "$BIN_DIR is already on your PATH." ;;
  *)
    warn "$BIN_DIR is not on your PATH. Add this line to your shell profile:"
    printf '\n        export PATH="%s:$PATH"\n\n' "$BIN_DIR"
    ;;
esac

# ------------------------------------------------------------------ 6. desktop icon
step "Creating the desktop icon"

DESKTOP="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
ICON="$DIR/webapp/static/aiws.png"

if [ "$(uname -s)" = "Darwin" ]; then
  # A .command file is double-clickable in Finder and needs no bundle. macOS will not take a
  # custom icon without one, so the file gets a clear name instead.
  if [ -d "$DESKTOP" ]; then
    cat > "$DESKTOP/AI Workflow Studio.command" <<EOF
#!/usr/bin/env bash
exec "$BIN_DIR/aiws"
EOF
    chmod +x "$DESKTOP/AI Workflow Studio.command"
    ok "Added to your Desktop. Double-click it to start the app."
  else
    info "No Desktop folder found; start the app with: aiws"
  fi
else
  APPS="$HOME/.local/share/applications"
  mkdir -p "$APPS"
  cat > "$APPS/ai-workflow-studio.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=AI Workflow Studio
Comment=Start AI Workflow Studio and open it in your browser
Exec=$BIN_DIR/aiws
Icon=$ICON
Terminal=true
Categories=Development;
EOF
  chmod +x "$APPS/ai-workflow-studio.desktop"
  ok "Added to your applications menu."
  if [ -d "$DESKTOP" ]; then
    cp "$APPS/ai-workflow-studio.desktop" "$DESKTOP/" 2>/dev/null || true
    chmod +x "$DESKTOP/ai-workflow-studio.desktop" 2>/dev/null || true
    # GNOME will not launch a desktop file it does not trust, and there is no way to grant
    # that from here, so say it rather than leaving the user with a dead icon.
    info "Also on your Desktop. GNOME may ask you to 'Allow Launching' the first time."
  fi
fi

# ------------------------------------------------------------------ done
printf '\n  %s%s%s\n' "$C_GRAY" "--------------------------------------------------------------" "$C_OFF"
if [ -n "$SIGNED_IN" ]; then
  printf '  %sReady.%s\n' "$C_GREEN" "$C_OFF"
else
  printf '  %sAlmost ready - one manual step left.%s\n\n' "$C_YELLOW" "$C_OFF"
  printf '      claude auth login\n\n'
  printf '  %sSigning in opens a browser, so it cannot be scripted. Everything else is done.%s\n' "$C_GRAY" "$C_OFF"
fi
printf '  %s%s%s\n\n' "$C_GRAY" "--------------------------------------------------------------" "$C_OFF"
printf '  Start the app:                 the "AI Workflow Studio" icon on your Desktop\n'
printf '  %sOr from a terminal:            aiws%s\n' "$C_GRAY" "$C_OFF"
printf '  %sUpdate to the latest code:     aiws update      (also checked on every start)%s\n' "$C_GRAY" "$C_OFF"
printf '  %sWhat is installed:             aiws version%s\n' "$C_GRAY" "$C_OFF"
printf '  %sIt opens at:                   http://127.0.0.1:8000%s\n' "$C_GRAY" "$C_OFF"
printf '  %sSkills in any Claude session:  /linhpham-diagram  /linhpham-technicalproposal  /linhpham-wbs%s\n\n' "$C_GRAY" "$C_OFF"

if [ -z "$NO_START" ]; then
  if [ -n "$SIGNED_IN" ]; then
    printf '  %sStarting ...%s\n' "$C_CYAN" "$C_OFF"
    exec "$PY" "$DIR/webapp/launch.py"
  else
    info "Not starting yet - sign in first, then run: aiws"
  fi
fi
