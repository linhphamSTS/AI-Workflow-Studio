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
# Recording "did it exist" is not enough, and that cost real damage once: on a machine where
# the app is already installed the shortcut DOES exist, the installer overwrites it to point at
# the sandbox, and a cleanup that only deletes what it created leaves the user's icon aimed at a
# directory this script is about to delete. So the original target is saved and put back.
$realDesktop = [Environment]::GetFolderPath('Desktop')
$realStart = Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'Microsoft\Windows\Start Menu\Programs'
$shortcuts = @(
    (Join-Path $realDesktop 'AI Workflow Studio.lnk'),
    (Join-Path $realStart 'AI Workflow Studio.lnk'),
    (Join-Path $realStart 'Stop AI Workflow Studio.lnk')
)
$shell = New-Object -ComObject WScript.Shell
$shortcutBefore = @{}
foreach ($s in $shortcuts) {
    if (Test-Path $s) {
        $o = $shell.CreateShortcut($s)
        $shortcutBefore[$s] = @{ Target = $o.TargetPath; Args = $o.Arguments
                                 Wd = $o.WorkingDirectory; Icon = $o.IconLocation
                                 Desc = $o.Description; Style = $o.WindowStyle }
    } else {
        $shortcutBefore[$s] = $null
    }
}

function Restore-Shortcuts {
    foreach ($s in $script:shortcuts) {
        $orig = $script:shortcutBefore[$s]
        if ($null -eq $orig) {
            if (Test-Path $s) {
                Remove-Item $s -Force -ErrorAction SilentlyContinue
                Write-Host "  removed $(Split-Path -Leaf $s) (this run created it)" -ForegroundColor Gray
            }
        } elseif (Test-Path $s) {
            $o = $script:shell.CreateShortcut($s)
            if ($o.TargetPath -ne $orig.Target -or $o.Arguments -ne $orig.Args) {
                $o.TargetPath = $orig.Target; $o.Arguments = $orig.Args
                $o.WorkingDirectory = $orig.Wd; $o.IconLocation = $orig.Icon
                $o.Description = $orig.Desc; $o.WindowStyle = $orig.Style
                $o.Save()
                Write-Host "  restored $(Split-Path -Leaf $s) to its original target" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host "sandbox   : $sandbox"
Write-Host "real HOME : $realHome (will be hidden from the installer)"
Write-Host ''

# A previous run that died after starting the server leaves it holding logs/aiws.log, and then
# the wipe below fails and this suite cannot run at all. Kill anything under the sandbox first.
$stale = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
           Where-Object { $_.CommandLine -like "*$(Split-Path -Leaf $sandbox)*" })
foreach ($p in $stale) {
    Write-Host "  killing a process left over from a previous run: $($p.ProcessId)" -ForegroundColor Yellow
    taskkill /F /T /PID $p.ProcessId 2>&1 | Out-Null
}
if ($stale) { Start-Sleep -Seconds 2 }
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

# Results gathered inside the try block, reported after it. Deliberately a FUNCTION with
# space-separated parameters rather than @(condition, detail) arrays: in an array literal the
# comma binds tighter than -eq/-ge/-match, so @($a -eq $b, $c) compares $a against the ARRAY
# ($b, $c) and dies on a type mismatch or an invalid regex escape. That bug was written twice
# in this file, fixed once, then reintroduced in the next block added. Removing the construct
# is the only fix that holds.
$script:collected = @()
function Record($name, $cond, $detail = '') {
    $script:collected += , @{ Name = $name; Ok = [bool]$cond; Detail = "$detail" }
}

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

    # ---- auto-update, exercised BEFORE .git is seeded --------------------------------------
    # It has to happen here: once a .git exists the updater deliberately stands down, so with
    # the seeding done first this whole path would never run and would look tested.
    Write-Host ''
    Write-Host "=== pass 1b: auto-update from a stale version ===" -ForegroundColor Magenta
    $script:autoUpdateResults = @{}
    $stampPath = Join-Path $installTo '.aiws-version'
    $dispatcher = Join-Path $installTo 'tools\aiws.py'
    $venvPy = Join-Path $installTo 'webapp\.venv\Scripts\python.exe'
    if ((Test-Path $stampPath) -and (Test-Path $dispatcher) -and (Test-Path $venvPy)) {
        $realSha = (Get-Content $stampPath -Raw | ConvertFrom-Json).sha
        $stale = '0' * 40
        $setStale = { @{ sha = $stale; branch = 'main'; installed = 'test' } | ConvertTo-Json |
                      Set-Content -Path $stampPath -Encoding ASCII }

        # (a) explicit: aiws update must notice it is behind and move the stamp forward
        & $setStale
        $out = (& $venvPy $dispatcher update 2>&1) -join "`n"
        $now = (Get-Content $stampPath -Raw | ConvertFrom-Json).sha
        Record 'explicit update advances the version' ($now -eq $realSha) $out

        # (b) implicit: the pre-start hook must do the same without being asked. Called
        #     directly rather than through `aiws` with no arguments, because that would go on
        #     to start a server this test has no way to shut down cleanly.
        & $setStale
        $hook = "import sys; sys.path.insert(0, r'$(Join-Path $installTo 'tools')'); " +
                "import aiws; aiws.check_quietly()"
        $out2 = (& $venvPy -c $hook 2>&1) -join "`n"
        $now2 = (Get-Content $stampPath -Raw | ConvertFrom-Json).sha
        Record 'start-up hook updates by itself' ($now2 -eq $realSha) $out2
        Record 'start-up hook says what it is doing' ($out2 -match 'newer version') $out2

        # (c) and it must NOT fire when there is nothing to do
        $out3 = (& $venvPy -c $hook 2>&1) -join "`n"
        Record 'start-up hook is silent when current' ($out3.Trim() -eq '') $out3
    } else {
        Record 'auto-update testable' $false 'stamp, dispatcher or venv missing'
    }

    # ---- start it the way the icon does, then stop it ---------------------------------------
    # Added because a stop that reported success left a descendant holding the socket: the
    # recorded pid died, the grandchild did not, and nothing noticed. The condition worth
    # asserting is that the PORT is free and no launch.py process survives.
    $pyw = Join-Path $installTo 'webapp\.venv\Scripts\pythonw.exe'
    $testPort = 8031        # not 8000: must not disturb a server the user is actually using
    if ((Test-Path $pyw) -and (Test-Path $dispatcher)) {
        $env:DIAGRAM_PORT = "$testPort"
        Start-Process -FilePath $pyw -ArgumentList """$dispatcher""", '--windowless' -WorkingDirectory $installTo
        Start-Sleep -Seconds 14
        $listening = { (netstat -ano | Select-String "127.0.0.1:$testPort" |
                        Select-String 'LISTENING' | Measure-Object).Count }
        Record 'icon start brings the server up' ((& $listening) -ge 1) 'nothing listening'

        $stopOut = (& $venvPy $dispatcher stop 2>&1) -join ' '
        Start-Sleep -Seconds 2
        Record 'stop frees the port' ((& $listening) -eq 0) "still listening; $stopOut"
        $orphans = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
                     Where-Object { $_.CommandLine -like "*$installTo*" })
        $orphanDetail = "$($orphans.Count) left: $($orphans.CommandLine -join ' | ')"
        Record 'stop leaves no orphan process' ($orphans.Count -eq 0) $orphanDetail
        foreach ($o in $orphans) { taskkill /F /T /PID $o.ProcessId 2>&1 | Out-Null }
        Remove-Item Env:\DIAGRAM_PORT -ErrorAction SilentlyContinue
    } else {
        Record 'round trip testable' $false 'pythonw or dispatcher missing'
    }

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

    # In the finally, not at the end of the script: an abort part way through still leaves a
    # shortcut aimed at the sandbox, and that is exactly how this went wrong before. The checks
    # below read the shortcut state captured here, so nothing is lost by restoring first.
    $script:lnkAfter = @{}
    foreach ($s in $shortcuts) {
        if (Test-Path $s) {
            $o = $shell.CreateShortcut($s)
            $script:lnkAfter[$s] = @{ Target = $o.TargetPath; Args = $o.Arguments; Icon = $o.IconLocation }
        }
    }
    Restore-Shortcuts

    # Prove the isolation held rather than assuming it, and REPAIR it if it did not.
    #
    # Matched on the sandbox's LEAF NAME, not its full path. $env:TEMP hands back an 8.3 short
    # name on this machine while a junction target is stored long, so "*$sandbox*" never matched
    # and this check stayed silent through a real leak: every one of the six live skill junctions
    # ended up pointing into a sandbox that was then deleted, and the skills stopped working.
    # Same 8.3 trap as the shortcut comparison, in a check whose whole job was to catch this.
    $leaf = Split-Path -Leaf $sandbox
    $leaked = @()
    foreach ($p in (Get-ChildItem $realHome -Directory -Filter '.claude*' -ErrorAction SilentlyContinue)) {
        foreach ($sk in (Get-ChildItem (Join-Path $p.FullName 'skills') -Force -ErrorAction SilentlyContinue)) {
            $target = (Get-Item -LiteralPath $sk.FullName -Force -ErrorAction SilentlyContinue).Target
            if ($target -and "$target" -like "*$leaf*") { $leaked += "$($p.Name)/$($sk.Name)" }
        }
    }
    if ($leaked.Count) {
        Write-Host ""
        Write-Host "  LEAK: these REAL skill links point into the sandbox: $($leaked -join ', ')" -ForegroundColor Red
        Write-Host "  Repairing them from the repo ..." -ForegroundColor Yellow
        $repo = Split-Path -Parent $PSScriptRoot
        foreach ($l in $leaked) {
            $full = Join-Path $realHome ($l -replace '/', '\skills\')
            cmd /c rmdir "$full" 2>&1 | Out-Null      # a dangling junction has to be removed first
        }
        & (Get-Command python).Source (Join-Path $repo 'install.py') 2>&1 | Out-Null
        Write-Host "  Repaired. This is a FAILURE of the isolation, not a warning." -ForegroundColor Red
        $script:leakDetected = $true
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

# The shortcut step, judged from the snapshot taken in the finally BEFORE the originals were
# put back, because by now the icons have been restored to whatever they were.
foreach ($s in $shortcuts) {
    $leaf = Split-Path -Leaf $s
    $where = if ($s -like "*Desktop*") { 'desktop' } else { 'start menu' }
    Check "$where shortcut created: $leaf" ($lnkAfter.ContainsKey($s)) "not found at $s"
}
$deskLnk = $shortcuts[0]
if ($lnkAfter.ContainsKey($deskLnk)) {
    $a = $lnkAfter[$deskLnk]
    # The whole point of the no-terminal work: the icon must run pythonw, which has no console,
    # and must pass --windowless so aiws.py redirects its output to a log instead of a dead
    # stdout. A .cmd or python.exe here would open the window this is meant to avoid.
    Check 'icon runs pythonw (no console)' ($a.Target -like '*pythonw.exe') "target is $($a.Target)"
    Check 'icon passes --windowless' ($a.Args -like '*--windowless*') "args are $($a.Args)"
    Check 'icon points at this install' ($a.Args -like "*aiws-it*") "args are $($a.Args)"
    Check 'icon carries the app icon' ($a.Icon -like '*aiws.ico*') "icon is $($a.Icon)"
}
$stopLnk = $shortcuts[2]
if ($lnkAfter.ContainsKey($stopLnk)) {
    Check 'stop entry calls stop' ($lnkAfter[$stopLnk].Args -like '* stop*') `
        "args are $($lnkAfter[$stopLnk].Args)"
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

# measured inside the try block: auto-update, and the start/stop round trip
foreach ($r in $collected) { Check $r.Name $r.Ok ($r.Detail -replace "`n", ' | ') }

# The suite must not damage the machine it runs on. This is a check, not a footnote.
Check 'no real skill link points into the sandbox' (-not $leakDetected) `
    'the isolation failed; the links were repaired but the harness is at fault'

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

Write-Host ''
if ($fails -eq 0 -and $ok) { Write-Host "  ALL CHECKS PASSED" -ForegroundColor Green }
else { Write-Host "  $fails CHECK(S) FAILED" -ForegroundColor Red }
Write-Host ''
Write-Host "sandbox left at $sandbox - delete it when done"
