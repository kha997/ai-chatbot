# Synthetic files only. Run with pwsh -NoProfile -File from the Issue #36 worktree.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../scripts/Copy-OllamaStorage.ps1')

function Check([bool]$pass, [string]$description) {
    if (-not $pass) { throw "Test failed: $description" }
}

function Expect-Failure([scriptblock]$action, [string]$pattern) {
    try { & $action; throw 'Expected a rejection' }
    catch { if ($_.Exception.Message -notmatch $pattern) { throw } }
}

function New-TestSparseFile([string]$path) {
    [IO.File]::WriteAllBytes($path, [byte[]]::new(0))
    fsutil sparse setflag $path | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create an NTFS sparse fixture.' }
    $stream = [IO.FileStream]::new($path, 'Open', 'Write')
    try {
        $stream.SetLength(1MB)
        $stream.WriteByte(65)
        $stream.Position = 1MB - 1
        $stream.WriteByte(90)
        $stream.Flush($true)
        Check ([OllamaStore36.Native]::Allocated($stream.SafeFileHandle) -lt 512KB) 'genuinely unallocated ranges'
    } finally { $stream.Dispose() }
}

$root = Join-Path (Split-Path (Split-Path $PSScriptRoot)) ("issue36-fixture-" + [guid]::NewGuid().ToString('N'))
$null = New-PrivateDirectory $root
try {
    $source = Join-Path $root 'source'
    $null = New-Item -ItemType Directory (Join-Path $source 'blobs') -Force
    $null = New-Item -ItemType Directory (Join-Path $source 'manifests') -Force
    $entries = @(1..5 | ForEach-Object {
        $temp = Join-Path $source "blob-$_"
        if ($_ -eq 1) {
            New-TestSparseFile $temp
        } else {
            [IO.File]::WriteAllText($temp, "synthetic blob $_")
        }
        $sha = (Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash.ToLowerInvariant()
        $relative = "blobs/sha256-$sha"
        [IO.File]::Move($temp, (Join-Path $source $relative))
        [pscustomobject]@{ path = $relative; sha256 = $sha; bytes = (Get-Item (Join-Path $source $relative)).Length }
    })
    $mf = Join-Path $source 'manifests/14b'
    [IO.File]::WriteAllText($mf, 'synthetic manifest')
    $entries += [pscustomobject]@{ path = 'manifests/14b'; sha256 = (Get-FileHash -LiteralPath $mf).Hash.ToLowerInvariant()
        bytes = (Get-Item $mf).Length }
    $total = ($entries | Measure-Object -Property bytes -Sum).Sum
    $sparse = Join-Path $source $entries[0].path
    $logical = [byte[]]::new(1MB)
    $logical[0] = 65
    $logical[-1] = 90
    Check ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($logical)) -ieq $entries[0].sha256) 'logical zero-hole hash'
    Expect-Failure { Get-StoragePath $sparse -File } 'file type'
    fsutil sparse setflag $mf | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cannot set the synthetic manifest sparse flag.' }
    try {
        Expect-Failure {
            Invoke-OllamaStorageCopy $source (Join-Path $root 'sparse-manifest') $entries $total 16MB 4096
        } 'file type'
    } finally {
        fsutil sparse setflag $mf 0 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Cannot restore the synthetic manifest flag.' }
    }
    'PASS sparse file rejected by the staging/destination guard'
    $cap = 16MB
    $dst = Join-Path $root 'published'
    $result = Invoke-OllamaStorageCopy $source $dst $entries $total $cap 4096
    Check ($result.files -eq 6 -and $result.bytes -eq $total -and $result.allocated_bound -le $cap -and
        $result.allocated_file_bytes -ge 4096 -and $result.allocated_file_bytes -le $result.allocated_bound) 'exact files and cap'
    Check ((Get-ChildItem -LiteralPath $dst -File -Recurse).Count -eq 6) 'published six files'
    Check (-not (([IO.File]::GetAttributes((Join-Path $dst $entries[0].path))) -band [IO.FileAttributes]::SparseFile)) 'output is non-sparse'
    Check (([IO.File]::GetAttributes($sparse) -band [IO.FileAttributes]::SparseFile) -ne 0) 'source attribute unchanged'
    foreach ($entry in $entries) {
        Check ((Get-FileHash (Join-Path $dst $entry.path)).Hash -eq $entry.sha256) 'published checksum'
        Check ((Get-FileHash (Join-Path $source $entry.path)).Hash -eq $entry.sha256) 'unchanged source checksum'
    }
    'PASS exact tiny copy from a genuine sparse source plus ordinary files'
    Expect-Failure { Invoke-OllamaStorageCopy $source $dst $entries $total $cap 4096 } 'destination'
    Expect-Failure { Invoke-OllamaStorageCopy $source (Join-Path $root 'overcap') $entries $total 1 4096 } 'cap'
    'PASS existing destination and allocation cap'

    $conflict = Join-Path $root 'conflict'
    Expect-Failure {
        Invoke-OllamaStorageCopy $source $conflict $entries $total $cap 4096 -BeforePromote {
            $null = New-Item -ItemType Directory $conflict
            [IO.File]::WriteAllText((Join-Path $conflict 'sentinel'), 'leave me')
        }
    } 'destination'
    Check ((Get-Content (Join-Path $conflict 'sentinel') -Raw) -eq 'leave me') 'foreign destination preserved'
    Check ((Get-ChildItem -LiteralPath $root -Filter '.ollama-stage-*' -Force).Count -eq 0) 'exact stage cleaned'
    'PASS publish collision and rollback'

    $toChange = Join-Path $source $entries[0].path
    Expect-Failure {
        Invoke-OllamaStorageCopy $source (Join-Path $root 'changed-source') $entries $total $cap 4096 -BeforePromote {
            [IO.File]::SetLastWriteTimeUtc($toChange, [DateTime]::UtcNow.AddHours(-2))
        }
    } 'Source changed'
    Check ((Get-ChildItem -LiteralPath $root -Filter '.ollama-stage-*' -Force).Count -eq 0) 'mutation stage cleaned'
    $oldMarker = Join-Path $root '.issue36-copy-attempt'
    [IO.File]::WriteAllText($oldMarker, 'synthetic spent Issue #36')
    $attempt = Open-StorageAttempt $root
    try { Expect-Failure { Open-StorageAttempt $root } 'already exists|being used' }
    finally { $attempt.Dispose() }
    Expect-Failure { Open-StorageAttempt $root } 'already exists'
    Check ((Get-Content -LiteralPath $oldMarker -Raw) -eq 'synthetic spent Issue #36' -and
        (Test-Path -LiteralPath (Join-Path $root '.issue39-copy-attempt'))) 'distinct one-use record'
    'PASS source timestamp drift, overlap and replay'

    $original = "$sparse.original"
    $before = Get-StoragePath $sparse -File -SourceBlob
    $lastWrite = [IO.File]::GetLastWriteTimeUtc($sparse)
    try {
        Expect-Failure {
            Invoke-OllamaStorageCopy $source (Join-Path $root 'swapped-source') $entries $total $cap 4096 -BeforePromote {
                [IO.File]::Move($sparse, $original)
                New-TestSparseFile $sparse
                [IO.File]::SetLastWriteTimeUtc($sparse, $lastWrite)
                $after = Get-StoragePath $sparse -File -SourceBlob
                Check ($before[1] -ne $after[1] -and $before[0] -ceq $after[0] -and
                    ($before[2..5] -join '|') -ceq ($after[2..5] -join '|')) 'only source identity changed'
                Check ((Get-FileHash -LiteralPath $sparse).Hash -ieq $entries[0].sha256) 'same replacement content'
            }
        } 'Source changed'
        Check ((Get-ChildItem -LiteralPath $root -Filter '.ollama-stage-*' -Force).Count -eq 0) 'identity-change stage cleaned'
    } finally {
        if (Test-Path -LiteralPath $original) {
            if (Test-Path -LiteralPath $sparse) { [IO.File]::Delete($sparse) }
            [IO.File]::Move($original, $sparse)
        }
    }
    'PASS same-bytes source replacement rejected'

    $junction = Join-Path $root 'junction'
    $null = New-Item -ItemType Junction -Path $junction -Target $source
    try {
        Expect-Failure { Invoke-OllamaStorageCopy $junction (Join-Path $root 'junction-rejected') $entries $total $cap 4096 } 'reparse'
    } finally { [IO.Directory]::Delete($junction, $false) }
    'PASS reparse path rejected'

    $first = Join-Path $source $entries[0].path
    $link = Join-Path $root 'hardlink'
    $null = New-Item -ItemType HardLink -Path $link -Target $first
    Expect-Failure { Invoke-OllamaStorageCopy $source (Join-Path $root 'link-rejected') $entries $total $cap 4096 } 'link'
    Remove-Item -LiteralPath $link
    Set-Content -LiteralPath $first -Stream unexpectedlyNamed -Value 'alternate stream'
    Expect-Failure { Invoke-OllamaStorageCopy $source (Join-Path $root 'stream-rejected') $entries $total $cap 4096 } 'NTFS data stream'
    Remove-Item -LiteralPath $first -Stream unexpectedlyNamed
    [IO.File]::WriteAllText($first, 'X' * $entries[0].bytes)
    Expect-Failure { Invoke-OllamaStorageCopy $source (Join-Path $root 'bad-hash') $entries $total $cap 4096 } 'hash'
    Check ((Get-ChildItem -LiteralPath $root -Filter '.ollama-stage-*' -Force).Count -eq 0) 'no stage for a corrupt source'
    'PASS hardlink and same-length corruption rejected'

    $sha = 'a' * 40
    $permit = [pscustomobject]@{id=3900; user=@{node_id='U_kgDODFyvuQ'}; author_association='OWNER';
        issue_url='https://api.github.com/repos/kha997/ai-chatbot/issues/39'; created_at='stamp'; updated_at='stamp';
        body=(Get-StorageApprovalText $sha)}
    Assert-StorageApproval $permit 3900 $sha
    Expect-Failure { Assert-StorageApproval $permit 3900 ('b' * 40) } 'exact Issue #39'
    $permit.issue_url = 'https://api.github.com/repos/kha997/ai-chatbot/issues/36'
    Expect-Failure { Assert-StorageApproval $permit 3900 $sha } 'exact Issue #39'
    'PASS exact Issue, technical SHA and manifest-bound approval gate'
} finally {
    $actual = (Resolve-Path -LiteralPath $root).Path
    if ($actual -eq $root -and (Split-Path $actual -Leaf) -match '^issue36-fixture-[0-9a-f]{32}$' -and
        (Split-Path $actual -Qualifier) -eq 'D:') {
        Remove-Item -LiteralPath $actual -Recurse
    }
}
