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

    Write-Host "=== running get.ps1 ===" -ForegroundColor Magenta
    & (Join-Path (Split-Path -Parent $PSScriptRoot) 'get.ps1') -Dir $installTo -NoStart
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

$skills = @('linhpham-diagram', 'linhpham-technicalproposal', 'linhpham-wbs')
foreach ($s in $skills) {
    $link = Join-Path $prof "skills\$s"
    Check "skill linked: $s" (Test-Path (Join-Path $link 'SKILL.md')) 'junction missing or empty'
}

# the launcher must point at the sandbox, with a real interpreter
if (Test-Path (Join-Path $installTo 'bin\aiws.cmd')) {
    $lc = Get-Content (Join-Path $installTo 'bin\aiws.cmd') -Raw
    Check 'launcher targets this install' ($lc -like "*$installTo*") 'wrong path in aiws.cmd'
    $exe = ([regex]'"([^"]+python[^"]*)"').Match($lc)
    Check 'launcher pins a real interpreter' ($exe.Success -and (Test-Path $exe.Groups[1].Value)) 'interpreter path not resolvable'
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
Write-Host "sandbox left at $sandbox for inspection"
