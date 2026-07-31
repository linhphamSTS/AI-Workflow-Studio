# End-to-end test of get.ps1 in a sandbox.
#
# Two things on this machine must not be harmed and both are easy to harm by accident:
#   - the REAL Claude profiles, because install.py re-links their skill junctions and this
#     test's install directory is about to be deleted;
#   - the REAL user PATH, because get.ps1 appends its bin directory to it.
# So: HOME is redirected to a throwaway profile, and PATH is snapshotted and restored.

$ErrorActionPreference = 'Stop'
# Deliberately a SHORT path, about as long as the real default (%LOCALAPPDATA%\AI-Workflow-Studio).
# The first run of this test used the scratchpad, whose path is long enough that Windows' own
# 260-character limit failed the copy - which was a real installer bug worth fixing, but testing
# from a pathological location would keep measuring Windows rather than the installer.
$sandbox = Join-Path $env:TEMP 'aiws-it'
$fakeHome = Join-Path $sandbox 'home'
$installTo = Join-Path $sandbox 'app'

$realHome = $env:USERPROFILE
$pathBefore = [Environment]::GetEnvironmentVariable('Path', 'User')

# GetFolderPath reads the shell folders from the registry, NOT $env:USERPROFILE, so the
# installer's shortcut step writes to the REAL Desktop even under a redirected HOME. Same trap
# as CLAUDE_CONFIG_DIR. Record what was there so anything this run creates can be removed
# again, and so a shortcut the user already had is never deleted.
$realDesktop = [Environment]::GetFolderPath('Desktop')
$realStart = Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'Microsoft\Windows\Start Menu\Programs'
$shortcuts = @((Join-Path $realDesktop 'AI Workflow Studio.lnk'), (Join-Path $realStart 'AI Workflow Studio.lnk'))
$shortcutExisted = @{}
foreach ($s in $shortcuts) { $shortcutExisted[$s] = Test-Path $s }

Write-Host "sandbox   : $sandbox"
Write-Host "real HOME : $realHome (will be hidden from the installer)"
Write-Host ''

if (Test-Path $sandbox) { Remove-Item $sandbox -Recurse -Force }
New-Item -ItemType Directory -Path $fakeHome -Force | Out-Null

# A throwaway Claude profile: deploy.py accepts a .claude* folder carrying at least two
# known signature files, so this is enough for it to link into and be verified.
$prof = Join-Path $fakeHome '.claude'
New-Item -ItemType Directory -Path $prof -Force | Out-Null
Set-Content -Path (Join-Path $prof '.credentials.json') -Value '{}' -Encoding ASCII
Set-Content -Path (Join-Path $prof 'history.jsonl') -Value '' -Encoding ASCII
New-Item -ItemType Directory -Path (Join-Path $prof 'projects') -Force | Out-Null

# Point the sandbox at the Graphviz already on this machine so the test does not spend
# minutes re-downloading 50 MB that has nothing to do with what is being tested.
$gvReal = Join-Path $realHome 'graphviz_portable'
if (Test-Path $gvReal) {
    cmd /c mklink /J "$fakeHome\graphviz_portable" "$gvReal" | Out-Null
    Write-Host "linked graphviz_portable into the sandbox"
}

$ok = $false
try {
    $env:USERPROFILE = $fakeHome
    $env:HOME = $fakeHome
    $env:APPDATA = Join-Path $fakeHome 'AppData\Roaming'
    New-Item -ItemType Directory -Path $env:APPDATA -Force | Out-Null
    # deploy.py honours CLAUDE_CONFIG_DIR IN ADDITION to scanning home, and on this machine
    # it points at a real profile. Redirecting HOME alone is not isolation: the first run of
    # this test repointed the real .claude-account2 skills at the sandbox, which was about to
    # be deleted. Clear it.
    $realConfigDir = $env:CLAUDE_CONFIG_DIR
    Remove-Item Env:\CLAUDE_CONFIG_DIR -ErrorAction SilentlyContinue

    $get = Join-Path (Split-Path -Parent $PSScriptRoot) 'get.ps1'

    Write-Host "=== pass 1: fresh install ===" -ForegroundColor Magenta
    & $get -Dir $installTo -NoStart

    # Seed the two things an update must not destroy, then install again over the top. .git is
    # the one that matters: a GitHub archive has no .git, so a mirroring copy would wipe the
    # history of anyone who pointed the installer at a clone.
    New-Item -ItemType Directory -Path (Join-Path $installTo '.git') -Force | Out-Null
    Set-Content -Path (Join-Path $installTo '.git\HEAD') -Value 'ref: refs/heads/main' -Encoding ASCII
    $wsFile = Join-Path $installTo 'webapp\workspaces\demo\meta.json'
    New-Item -ItemType Directory -Path (Split-Path $wsFile) -Force | Out-Null
    Set-Content -Path $wsFile -Value '{"id":"demo"}' -Encoding ASCII

    Write-Host ''
    Write-Host "=== pass 2: update over the existing install ===" -ForegroundColor Magenta
    & $get -Dir $installTo -NoStart
    $ok = $true
}
finally {
    $env:USERPROFILE = $realHome
    $env:HOME = $realHome
    if ($realConfigDir) { $env:CLAUDE_CONFIG_DIR = $realConfigDir }

    # Prove the isolation held rather than assuming it: no real profile may point at the sandbox.
    foreach ($p in (Get-ChildItem $realHome -Directory -Filter '.claude*' -ErrorAction SilentlyContinue)) {
        foreach ($sk in (Get-ChildItem (Join-Path $p.FullName 'skills') -Directory -ErrorAction SilentlyContinue)) {
            $target = (Get-Item $sk.FullName).Target
            if ($target -and "$target" -like "*$sandbox*") {
                Write-Host "  LEAK: $($p.Name)/$($sk.Name) points into the sandbox" -ForegroundColor Red
            }
        }
    }
    $pathAfter = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($pathAfter -ne $pathBefore) {
        [Environment]::SetEnvironmentVariable('Path', $pathBefore, 'User')
        Write-Host ''
        Write-Host "restored the user PATH (installer had appended its bin dir)" -ForegroundColor Yellow
    } else {
        Write-Host ''
        Write-Host "user PATH unchanged" -ForegroundColor Gray
    }
}

Write-Host ''
Write-Host "=== checks ===" -ForegroundColor Magenta
$fails = 0
function Check($name, $cond, $detail) {
    if ($cond) { Write-Host "  PASS  $name" -ForegroundColor Green }
    else { Write-Host "  FAIL  $name  ($detail)" -ForegroundColor Red; $script:fails++ }
}

Check 'repo downloaded'        (Test-Path (Join-Path $installTo 'install.py')) 'install.py missing'
Check 'webapp present'         (Test-Path (Join-Path $installTo 'webapp\server.py')) 'server.py missing'
Check 'venv built'             (Test-Path (Join-Path $installTo 'webapp\.venv\Scripts\python.exe')) 'no venv interpreter'
Check 'aiws launcher written'  (Test-Path (Join-Path $installTo 'bin\aiws.cmd')) 'aiws.cmd missing'

# what the update pass must have preserved
Check 'update keeps .git'      (Test-Path (Join-Path $installTo '.git\HEAD')) 'the mirror copy deleted a clone history'
Check 'update keeps workspaces' (Test-Path (Join-Path $installTo 'webapp\workspaces\demo\meta.json')) 'generated work was deleted'
Check 'update keeps the venv'  (Test-Path (Join-Path $installTo 'webapp\.venv\Scripts\python.exe')) 'the venv was deleted'

# the shortcut step, checked against the REAL desktop because that is where it lands
foreach ($s in $shortcuts) {
    $name = if ($s -like "*Desktop*") { 'desktop shortcut' } else { 'start menu shortcut' }
    Check "$name created" (Test-Path $s) "not found at $s"
}
$deskLnk = $shortcuts[0]
if (Test-Path $deskLnk) {
    $sc = (New-Object -ComObject WScript.Shell).CreateShortcut($deskLnk)
    # Do not compare the two paths as strings. $env:TEMP hands back an 8.3 short name here, so
    # the .cmd holds the SHORT spelling (written from -Dir verbatim) while Windows stores the
    # LONG one in the .lnk, and neither Resolve-Path nor FileSystemObject expands the other.
    # Compare what the shortcut actually opens instead: the file it points at must BE this
    # install's launcher. That is the property worth asserting, and it cannot be fooled by
    # spelling.
    $mine = Join-Path $installTo 'bin\aiws.cmd'
    $same = (Test-Path $sc.TargetPath) -and
            ((Get-Content $sc.TargetPath -Raw) -eq (Get-Content $mine -Raw))
    Check 'shortcut opens this install''s launcher' $same "points at $($sc.TargetPath)"
    Check 'shortcut carries the app icon' ($sc.IconLocation -like '*aiws.ico*') "icon is $($sc.IconLocation)"
}

$skills = @('linhpham-diagram', 'linhpham-technicalproposal', 'linhpham-wbs')
foreach ($s in $skills) {
    $link = Join-Path $prof "skills\$s"
    Check "skill linked: $s" (Test-Path (Join-Path $link 'SKILL.md')) 'junction missing or empty'
}

# the launcher must point at the sandbox, with a real interpreter
if (Test-Path (Join-Path $installTo 'bin\aiws.cmd')) {
    $lc = Get-Content (Join-Path $installTo 'bin\aiws.cmd') -Raw
    # $env:TEMP hands back the 8.3 short form on this machine while the file holds the long
    # one, so compare resolved paths. Comparing the strings reports a failure that is not real.
    $longInstall = (Resolve-Path $installTo).Path
    Check 'launcher targets this install' ($lc -like "*$longInstall*") 'wrong path in aiws.cmd'

    # Take the first quoted path on the command line, whatever it is called: it may be a venv
    # python, a system python, or the py launcher, and hard-coding "python" missed py.exe.
    $exe = ([regex]'(?m)^"([^"]+)"').Match($lc)
    Check 'launcher pins a real interpreter' ($exe.Success -and (Test-Path $exe.Groups[1].Value)) `
        "first quoted token is not an existing file: $($exe.Groups[1].Value)"
    Check 'launcher uses the venv interpreter' ($exe.Groups[1].Value -like '*\.venv\Scripts\python.exe') `
        "pinned $($exe.Groups[1].Value) instead of the venv python"
    Check 'launcher goes through the aiws dispatcher' ($lc -like '*tools\aiws.py*') `
        'calls launch.py directly, so update/version would not exist'
}

# the version stamp, and the update commands built on it
$stamp = Join-Path $installTo '.aiws-version'
Check 'version stamp written' (Test-Path $stamp) 'no .aiws-version, so update cannot tell if it is behind'
if (Test-Path $stamp) {
    $sha = (Get-Content $stamp -Raw | ConvertFrom-Json).sha
    Check 'version stamp holds a commit' ($sha -match '^[0-9a-f]{40}$') "sha is '$sha'"
}
$vpy2 = Join-Path $installTo 'webapp\.venv\Scripts\python.exe'
$disp = Join-Path $installTo 'tools\aiws.py'
# Checked as its own condition, not folded into the if below: the first run of this suite
# skipped the dispatcher tests in silence because the file was not in the archive yet, and a
# launcher pointing at a file that does not exist had reported everything green.
Check 'dispatcher present in the install' (Test-Path $disp) 'tools/aiws.py is missing, so aiws would fail to start'
if ((Test-Path $vpy2) -and (Test-Path $disp)) {
    $vout = (& $vpy2 $disp version 2>&1) -join "`n"
    Check 'aiws version reports the install' ($vout -like "*$installTo*" -or $vout -like '*installed*') $vout
    # pass 2 seeded a .git, so the updater must refuse to mirror over a working copy
    $uout = (& $vpy2 $disp update 2>&1) -join "`n"
    Check 'aiws update refuses to overwrite a git checkout' ($uout -like '*git working copy*') $uout
}

# the venv must actually be able to import what the app needs
$vpy = Join-Path $installTo 'webapp\.venv\Scripts\python.exe'
if (Test-Path $vpy) {
    & $vpy -c "import fastapi, uvicorn, PIL, docx, openpyxl, fitz; print('deps import OK')"
    Check 'venv dependencies import' ($LASTEXITCODE -eq 0) 'an import failed'
}

# Put the desktop back the way it was. Leaving a shortcut that points into a sandbox about to
# be deleted would be worse than never having tested the step.
foreach ($s in $shortcuts) {
    if (-not $shortcutExisted[$s] -and (Test-Path $s)) {
        Remove-Item $s -Force -ErrorAction SilentlyContinue
        Write-Host "  cleaned up $(Split-Path -Leaf $s) from $(Split-Path -Parent $s)" -ForegroundColor Gray
    }
}

Write-Host ''
if ($fails -eq 0 -and $ok) { Write-Host "  ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "  $fails CHECK(S) FAILED" -ForegroundColor Red }
Write-Host ''
Write-Host "sandbox left at $sandbox - delete it when done"
