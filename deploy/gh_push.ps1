param(
  [string]$Repo = "ChaoyuZhang1/exchangekit",
  [string]$Message = "Update site"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$exists = $true
try { gh repo view $Repo --json name 2>$null | Out-Null } catch { $exists = $false }
if (-not $exists) {
  gh repo create $Repo --public --description "Exchange trading days and market holidays (static site)" 2>&1 | Select-Object -Last 1
}

$headSha = $null
try { $headSha = (gh api "repos/$Repo/git/refs/heads/main" --jq ".object.sha" 2>$null).Trim() } catch { $headSha = $null }
if (-not $headSha) {
  $initB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("# $Repo"))
  $initPayload = @{ message = "init"; content = $initB64; branch = "main" } | ConvertTo-Json -Compress
  $tmpInit = Join-Path $env:TEMP "gh_init.json"
  [System.IO.File]::WriteAllText($tmpInit, $initPayload, [System.Text.UTF8Encoding]::new($false))
  $headSha = (gh api "repos/$Repo/contents/.gitkeep" --method PUT --input $tmpInit --jq ".commit.sha").Trim()
  Remove-Item $tmpInit -Force
}
$baseTree = (gh api "repos/$Repo/git/commits/$headSha" --jq ".tree.sha").Trim()

$exclude = @("dist", "__pycache__", ".git", "node_modules", ".wrangler", ".pytest_cache")
$files = Get-ChildItem -Recurse -File | Where-Object {
  $rel = $_.FullName.Substring($Root.Length + 1)
  $parts = $rel -split "[\\/]"
  -not ($parts | Where-Object { $exclude -contains $_ })
}
Write-Host "uploading $($files.Count) files to $Repo"

$entries = @()
foreach ($f in $files) {
  $rel = $f.FullName.Substring($Root.Length + 1).Replace("\", "/")
  $b64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($f.FullName))
  $payload = @{ content = $b64; encoding = "base64" } | ConvertTo-Json -Compress
  $tmp = Join-Path $env:TEMP "gh_blob.json"
  [System.IO.File]::WriteAllText($tmp, $payload, [System.Text.UTF8Encoding]::new($false))
  $sha = (gh api "repos/$Repo/git/blobs" --method POST --input $tmp --jq ".sha").Trim()
  Remove-Item $tmp -Force
  $entries += @{ path = $rel; mode = "100644"; type = "blob"; sha = $sha }
}

$treePayload = @{ base_tree = $baseTree; tree = $entries } | ConvertTo-Json -Depth 8 -Compress
$tmpTree = Join-Path $env:TEMP "gh_tree.json"
[System.IO.File]::WriteAllText($tmpTree, $treePayload, [System.Text.UTF8Encoding]::new($false))
$treeSha = (gh api "repos/$Repo/git/trees" --method POST --input $tmpTree --jq ".sha").Trim()
Remove-Item $tmpTree -Force

$commitPayload = @{ message = $Message; tree = $treeSha; parents = @($headSha) } | ConvertTo-Json -Compress
$tmpCommit = Join-Path $env:TEMP "gh_commit.json"
[System.IO.File]::WriteAllText($tmpCommit, $commitPayload, [System.Text.UTF8Encoding]::new($false))
$commitSha = (gh api "repos/$Repo/git/commits" --method POST --input $tmpCommit --jq ".sha").Trim()
Remove-Item $tmpCommit -Force

$refPayload = @{ sha = $commitSha; force = $true } | ConvertTo-Json -Compress
$tmpRef = Join-Path $env:TEMP "gh_ref.json"
[System.IO.File]::WriteAllText($tmpRef, $refPayload, [System.Text.UTF8Encoding]::new($false))
gh api "repos/$Repo/git/refs/heads/main" --method PATCH --input $tmpRef --jq ".object.sha" | Out-Null
Remove-Item $tmpRef -Force
Write-Host "pushed $Repo -> $commitSha"
