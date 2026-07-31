<#
.SYNOPSIS
  One-command installer for AI Workflow Studio (Windows).

.DESCRIPTION
  Run this on a machine that has nothing installed:

      irm https://raw.githubusercontent.com/linhphamSTS/AI-Workflow-Studio/main/get.ps1 | iex

  It downloads the repo, makes sure a Python is available (fetching one through uv if the
  machine has none), sets up the web app, deploys every skill into every Claude Code
  profile, offers to install the Claude Code CLI if it is missing, checks whether you are
  signed in, adds an `aiws` command to your PATH, and starts the app.

  Signing in is the one step that cannot be automated: it opens a browser. If you are not
  signed in, the installer says so and tells you the command to run.

  Nothing here needs Administrator rights, and nothing is installed system-wide.

.PARAMETER Yes
  Do not ask anything. Accepts the Claude Code CLI install on your behalf.

.PARAMETER NoStart
  Set everything up but do not launch the app.

.PARAMETER Dir
  Where to install. Defaults to $env:LOCALAPPDATA\AI-Workflow-Studio.

.NOTES
  Piping into iex cannot pass parameters. Either set AIWS_YES=1 / AIWS_NO_START=1 /
  AIWS_DIR=..., or invoke it as a script block:

      & ([scriptblock]::Create((irm https://raw.githubusercontent.com/linhphamSTS/AI-Workflow-Studio/main/get.ps1))) -Yes
#>
[CmdletBinding()]
param(
    [switch]$Yes,
    [switch]$NoStart,
    [string]$Dir,
    # Treat the directory this script sits in AS the install and skip the download. For a
    # developer working in a clone: it wires up the aiws command and the Desktop icon without
    # mirroring GitHub over the work in progress.
    [switch]$Here
)

$ErrorActionPreference = 'Stop'
# Old PowerShell 5.1 hosts still default to TLS 1.0, which GitHub refuses.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Environment fallbacks, because `irm | iex` has no way to pass parameters.
if ($env:AIWS_YES -eq '1')      { $Yes = $true }
if ($env:AIWS_NO_START -eq '1') { $NoStart = $true }
if (-not $Dir -and $env:AIWS_DIR) { $Dir = $env:AIWS_DIR }

$Repo      = 'linhphamSTS/AI-Workflow-Studio'
$Branch    = 'main'
$AppName   = 'AI Workflow Studio'
$BinDir    = $null
# Paths, relative to the install directory, that an update must never delete. /MIR removes
# anything the archive does not contain, so everything the USER owns has to be named here:
#   .git              - a GitHub archive has no .git, so installing over a CLONE would
#                       otherwise delete its entire history. Destroying a repository is not
#                       an acceptable outcome of pointing -Dir at the wrong place.
#   webapp/workspaces - generated work that exists nowhere else.
#   webapp/.venv      - expensive to rebuild, and not in the archive either.
$Keep      = @('.git', 'webapp\workspaces', 'webapp\.venv')

if ($env:AIWS_HERE -eq '1') { $Here = $true }

$script:StepNo = 0
function Write-Step($text) {
    $script:StepNo++
    Write-Host ''
    Write-Host "[$script:StepNo] $text" -ForegroundColor Cyan
}
function Write-Ok($text)   { Write-Host "    $text" -ForegroundColor Green }
function Write-Info($text) { Write-Host "    $text" -ForegroundColor Gray }
function Write-Warn($text) { Write-Host "    $text" -ForegroundColor Yellow }
function Fail($text) {
    Write-Host ''
    Write-Host "  Install failed: $text" -ForegroundColor Red
    Write-Host ''
    exit 1
}

function Confirm-Action($question) {
    if ($Yes) { return $true }
    # A non-interactive host (CI, a scheduled task) must not hang on a prompt.
    if ([Console]::IsInputRedirected) {
        Write-Info 'Non-interactive session, assuming no. Re-run with -Yes to accept.'
        return $false
    }
    while ($true) {
        $a = (Read-Host "    $question [Y/n]").Trim().ToLower()
        if ($a -eq '' -or $a -eq 'y' -or $a -eq 'yes') { return $true }
        if ($a -eq 'n' -or $a -eq 'no') { return $false }
    }
}

# Resolved here, below the helpers, because -Here can fail and Fail is defined above.
if ($Here) {
    if (-not $PSScriptRoot) { Fail '-Here needs this script saved to disk. Save it, or pass -Dir.' }
    $Dir = $PSScriptRoot
}
if (-not $Dir) { $Dir = Join-Path $env:LOCALAPPDATA 'AI-Workflow-Studio' }
$BinDir = Join-Path $Dir 'bin'

Write-Host ''
Write-Host "  $AppName" -ForegroundColor White
Write-Host '  SA-grade deliverables, from a prompt' -ForegroundColor DarkGray
Write-Host "  $(if ($Here) { 'Wiring up' } else { 'Installing into' }) $Dir" -ForegroundColor DarkGray

# Some icon files in this repo sit ~140 characters deep on their own. Copying is handled by
# robocopy, which copes, but pip building the virtual-env underneath a long prefix does not
# unless Windows long paths are enabled, so say so before the slow part rather than after.
if ($Dir.Length -gt 90) {
    Write-Warn "That path is $($Dir.Length) characters deep. Windows limits paths to 260 by default,"
    Write-Warn 'and dependency installation can fail underneath a long one. Pass -Dir with a'
    Write-Warn 'shorter path, or enable long path support, if step 3 fails.'
}

# ---------------------------------------------------------------- 1. get the code
if ($Here) {
    Write-Step 'Using the code already in this folder'
    if (-not (Test-Path (Join-Path $Dir 'install.py'))) { Fail "$Dir does not look like the repo (no install.py)." }
    Write-Ok 'Skipping the download.'
} else {

Write-Step 'Downloading the repository'

# Record which commit this install came from, so `aiws update` can tell whether there is
# anything to do without downloading 65 MB to find out.
$headSha = $null
try {
    # Two PowerShell 5.1 details, both of which silently broke this the first time:
    # User-Agent is a restricted header and must be its own parameter, not a -Headers entry;
    # and .Content comes back as a BYTE ARRAY whenever the content type is not one PS treats
    # as text, which application/vnd.github.sha is not. Calling .Trim() on it just throws.
    $resp = Invoke-WebRequest -Uri "https://api.github.com/repos/$Repo/commits/$Branch" `
        -Headers @{ 'Accept' = 'application/vnd.github.sha' } `
        -UserAgent 'aiws-installer' -UseBasicParsing
    $raw = if ($resp.Content -is [byte[]]) { [Text.Encoding]::UTF8.GetString($resp.Content) } else { [string]$resp.Content }
    if ($raw.Trim() -match '^[0-9a-f]{40}$') { $headSha = $raw.Trim() }
} catch { }
if (-not $headSha) { Write-Info 'Could not read the current commit; "aiws update" will still work, just less cheaply.' }

$isUpdate = Test-Path (Join-Path $Dir 'install.py')
$staging  = Join-Path ([IO.Path]::GetTempPath()) ("aiws-" + [Guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $staging -Force | Out-Null

try {
    $zip = Join-Path $staging 'repo.zip'
    Write-Info 'About 65 MB, so this is the slow step.'
    $progressPreference = 'SilentlyContinue'   # the progress bar makes IWR far slower
    Invoke-WebRequest -Uri "https://github.com/$Repo/archive/refs/heads/$Branch.zip" -OutFile $zip -UseBasicParsing
    $progressPreference = 'Continue'

    Expand-Archive -Path $zip -DestinationPath $staging -Force
    $src = Get-ChildItem -Path $staging -Directory | Where-Object { $_.Name -like 'AI-Workflow-Studio-*' } | Select-Object -First 1
    if (-not $src) { Fail 'the downloaded archive did not contain the expected folder.' }

    if ($isUpdate) { Write-Info 'Existing install found, updating it and leaving your workspaces alone.' }
    New-Item -ItemType Directory -Path $Dir -Force | Out-Null

    # robocopy rather than Copy-Item, for one specific reason: this repo contains icon files
    # whose paths run past Windows' 260-character limit once an install directory is prefixed,
    # and Copy-Item fails outright on them. robocopy handles long paths natively.
    #
    # /MIR removes anything in the destination that is not in the archive, which is right for
    # repo files and emphatically wrong for the user's own data, hence /XD. On a first install
    # the destination is empty, so the same command serves both cases.
    $xd = @()
    foreach ($k in $Keep) { $xd += '/XD'; $xd += (Join-Path $Dir $k) }
    $null = & robocopy $src.FullName $Dir /MIR /NFL /NDL /NJH /NJS /NP /R:2 /W:1 @xd
    $rc = $LASTEXITCODE
    $global:LASTEXITCODE = 0          # robocopy uses 0-7 for success; leaving it set trips later checks
    if ($rc -ge 8) { Fail "copying the files failed (robocopy exit $rc)." }
    if ($headSha) {
        @{ sha = $headSha; branch = $Branch; installed = (Get-Date).ToString('s') } |
            ConvertTo-Json | Set-Content -Path (Join-Path $Dir '.aiws-version') -Encoding ASCII
    }
    Write-Ok ($(if ($isUpdate) { 'Updated.' } else { 'Downloaded.' }))
}
finally {
    Remove-Item -Path $staging -Recurse -Force -ErrorAction SilentlyContinue
}

}   # end of the download branch skipped by -Here

# ---------------------------------------------------------------- 2. a working Python
Write-Step 'Looking for Python 3.10 or newer'

function Test-Python($exe, $preArgs) {
    # Ask the interpreter itself. Windows ships a "python" stub that opens the Store and
    # reports no version at all, so parsing --version output is not enough to trust it.
    #
    # The probe contains NO quote characters on purpose. Windows PowerShell 5.1 strips
    # embedded double quotes when it hands an argument to a native executable, so a probe
    # written the obvious way arrives at python as print(%d.%d % ...) and dies with a
    # SyntaxError. That failure looks exactly like "no Python here", and the installer
    # would go and download one on a machine that already had a perfectly good one.
    try {
        $all = @()
        if ($preArgs) { $all += $preArgs }
        $all += @('-c', 'import sys; print(sys.version.split()[0])')
        $out = & $exe @all 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
        $parts = ("$out".Trim() -split '\.')
        if ($parts.Count -lt 2) { return $null }
        $v = [version]("{0}.{1}" -f $parts[0], $parts[1])
        if ($v -ge [version]'3.10') { return $v }
    } catch { }
    return $null
}

$py = $null; $pyArgs = @()
foreach ($cand in @(@('py', @('-3')), @('python', @()), @('python3', @()))) {
    $exe = $cand[0]
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
    $v = Test-Python $exe $cand[1]
    if ($v) { $py = (Get-Command $exe).Source; $pyArgs = $cand[1]; Write-Ok "Found Python $v ($exe)"; break }
}

if (-not $py) {
    Write-Info 'No suitable Python on this machine. Fetching a private one with uv.'
    Write-Info 'It goes in uv''s own directory and does not become your system Python.'
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Info 'Installing uv (a single binary, no admin rights needed) ...'
        try { Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression }
        catch { Fail "could not install uv: $($_.Exception.Message)" }
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Fail 'uv installed but is not on PATH. Open a new terminal and run this installer again.'
    }
    & uv python install 3.12
    if ($LASTEXITCODE -ne 0) { Fail 'uv could not install Python 3.12.' }
    $found = (& uv python find 3.12 2>$null | Select-Object -First 1)
    if (-not $found -or -not (Test-Path $found)) { Fail 'uv installed Python but its path could not be resolved.' }
    $py = $found; $pyArgs = @()
    Write-Ok "Using $py"
}

# ---------------------------------------------------------------- 3. skills + web app
Write-Step 'Deploying the skills and setting up the web app'
Write-Info 'Creates a private virtual-env, installs dependencies, and fetches Graphviz.'

Push-Location $Dir
try {
    $args2 = @()
    if ($pyArgs) { $args2 += $pyArgs }
    $args2 += (Join-Path $Dir 'install.py')
    & $py @args2
    if ($LASTEXITCODE -ne 0) { Write-Warn 'install.py reported warnings, see the output above.' }
}
finally { Pop-Location }

# ---------------------------------------------------------------- 4. the Claude Code CLI
Write-Step 'Checking the Claude Code CLI'

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
    Write-Warn 'Not installed. The skills and the web app both drive it, so it is required.'
    if (Confirm-Action 'Install Claude Code now (from claude.ai, no admin rights)?') {
        try { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression }
        catch { Write-Warn "Automatic install failed: $($_.Exception.Message)" }
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
        $claude = Get-Command claude -ErrorAction SilentlyContinue
        if ($claude) { Write-Ok 'Installed.' }
    } else {
        Write-Info 'Skipped. Install it later: irm https://claude.ai/install.ps1 | iex'
    }
}

$signedIn = $false
if ($claude) {
    try {
        $status = & $claude.Source auth status --json 2>$null | ConvertFrom-Json
        if ($status.loggedIn) {
            $who = if ($status.email) { $status.email } elseif ($status.orgName) { $status.orgName } else { '' }
            Write-Ok ("Signed in" + $(if ($who) { " as $who" } else { '' }))
            $signedIn = $true
        }
    } catch { }
    if (-not $signedIn) { Write-Warn 'Installed but NOT signed in.' }
}

# ---------------------------------------------------------------- 5. the aiws command
Write-Step 'Adding the aiws command'

New-Item -ItemType Directory -Path $BinDir -Force | Out-Null

# The interpreter is pinned rather than looked up at run time: when uv supplied the Python it
# is deliberately not on PATH, so a launcher that searched for one would find nothing.
#
# Prefer the virtual-env interpreter that step 3 just built. It is an absolute path to one
# exact Python, whereas the bootstrap interpreter may be the "py" launcher, which selects a
# version from its own rules and needs -3 to be trusted. launch.py re-execs into this venv
# anyway, so naming it directly removes a whole class of "which Python did that pick" bug.
$venvPy = Join-Path $Dir 'webapp\.venv\Scripts\python.exe'
if (Test-Path $venvPy) {
    $runCmd = """$venvPy"""
} else {
    # No venv (step 3 failed): fall back to the bootstrap interpreter, WITH the arguments the
    # probe used. Dropping them turns "py -3" into "py", which is not the same interpreter.
    $runCmd = (@("""$py""") + $pyArgs) -join ' '
}
# Calls tools/aiws.py rather than launch.py directly: that is where `aiws update`, the
# version report and the pre-start update check live, shared with the macOS and Linux launcher.
$launcher = @"
@echo off
REM Start $AppName. Generated by get.ps1 - re-run the installer to regenerate.
$runCmd "$Dir\tools\aiws.py" %*
"@
Set-Content -Path (Join-Path $BinDir 'aiws.cmd') -Value $launcher -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not $userPath) { $userPath = '' }
if (($userPath -split ';') -notcontains $BinDir) {
    [Environment]::SetEnvironmentVariable('Path', ($userPath.TrimEnd(';') + ";$BinDir").TrimStart(';'), 'User')
    Write-Ok 'Added to your PATH. A new terminal will pick it up.'
} else {
    Write-Ok 'Already on your PATH.'
}
$env:Path = "$env:Path;$BinDir"

# ---------------------------------------------------------------- 6. desktop icon
Write-Step 'Creating the desktop icon'

$icon = Join-Path $Dir 'webapp\static\aiws.ico'

# pythonw.exe, not python.exe and not the .cmd: either of those opens a console window, and a
# .lnk cannot suppress one belonging to a process it starts. pythonw has no console at all.
# tools/aiws.py notices this (sys.stdout is None) and writes to logs/aiws.log instead.
$pyw = Join-Path $Dir 'webapp\.venv\Scripts\pythonw.exe'
if (-not (Test-Path $pyw)) { $pyw = $null }

function New-AiwsShortcut($path, $arguments, $description) {
    $sc = (New-Object -ComObject WScript.Shell).CreateShortcut($path)
    $sc.TargetPath = $pyw
    $sc.Arguments = $arguments
    $sc.WorkingDirectory = $Dir
    $sc.Description = $description
    if (Test-Path $icon) { $sc.IconLocation = $icon }
    $sc.Save()
}

if (-not $pyw) {
    Write-Warn 'pythonw.exe was not found in the virtual-env, so no icon was created.'
    Write-Info 'Start the app with: aiws'
} else {
    try {
        $run  = """$Dir\tools\aiws.py"" --windowless"
        $stop = """$Dir\tools\aiws.py"" stop"

        # GetFolderPath, not "$env:USERPROFILE\Desktop": on a machine where OneDrive has taken
        # over the Desktop, the literal path is not where the icons actually appear.
        $desktop = [Environment]::GetFolderPath('Desktop')
        New-AiwsShortcut (Join-Path $desktop 'AI Workflow Studio.lnk') $run `
            'Start AI Workflow Studio and open it in your browser'
        Write-Ok 'Added to your Desktop. Double-click it: no terminal window appears.'

        $startMenu = Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'Microsoft\Windows\Start Menu\Programs'
        if (Test-Path $startMenu) {
            New-AiwsShortcut (Join-Path $startMenu 'AI Workflow Studio.lnk') $run `
                'Start AI Workflow Studio and open it in your browser'
            # Without a console there is no Ctrl+C, so the way to stop it has to be visible
            # somewhere a person will find it.
            New-AiwsShortcut (Join-Path $startMenu 'Stop AI Workflow Studio.lnk') $stop `
                'Stop the AI Workflow Studio server'
            Write-Info 'In the Start menu too, with a "Stop AI Workflow Studio" entry.'
        }
    } catch {
        Write-Warn "Could not create the shortcut: $($_.Exception.Message)"
        Write-Info  "You can still start the app by running: aiws"
    }
}

# ---------------------------------------------------------------- done
Write-Host ''
Write-Host ('  ' + ('-' * 62)) -ForegroundColor DarkGray
if ($signedIn) {
    Write-Host '  Ready.' -ForegroundColor Green
} else {
    Write-Host '  Almost ready - one manual step left.' -ForegroundColor Yellow
    Write-Host ''
    Write-Host '      claude auth login' -ForegroundColor White
    Write-Host ''
    Write-Host '  Signing in opens a browser, so it cannot be scripted. Everything else is done.' -ForegroundColor Gray
}
Write-Host ('  ' + ('-' * 62)) -ForegroundColor DarkGray
Write-Host ''
Write-Host '  Start the app:                 the "AI Workflow Studio" icon on your Desktop' -ForegroundColor White
Write-Host '  Or from a terminal:            aiws' -ForegroundColor Gray
Write-Host '  Stop it again:                 aiws stop        (or the Start-menu Stop entry)' -ForegroundColor Gray
Write-Host '  Update to the latest code:     aiws update      (also checked on every start)' -ForegroundColor Gray
Write-Host '  What is installed:             aiws version' -ForegroundColor Gray
Write-Host '  It opens at:                   http://127.0.0.1:8000' -ForegroundColor Gray
Write-Host '  Skills in any Claude session:  /linhpham-diagram  /linhpham-technicalproposal  /linhpham-wbs' -ForegroundColor Gray
Write-Host ''

if (-not $NoStart) {
    if ($signedIn) {
        Write-Host '  Starting ...' -ForegroundColor Cyan
        & $py (Join-Path $Dir 'webapp\launch.py')
    } else {
        Write-Info 'Not starting yet - sign in first, then run: aiws'
    }
}
