param([long]$ApprovalCommentId = 0)

if (-not ('OllamaStore36.Native' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;
namespace OllamaStore36 {
    public static class Native {
        [StructLayout(LayoutKind.Sequential)]
        private struct Info {
            public uint Attributes, CreatedLow, CreatedHigh, AccessLow, AccessHigh, WriteLow, WriteHigh;
            public uint Volume, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct StandardInfo {
            public long AllocationSize, EndOfFile;
            public uint Links;
            public byte DeletePending, Directory;
        }
        [StructLayout(LayoutKind.Sequential)]
        private struct SecurityAttributes {
            public int Length;
            public IntPtr Descriptor;
            public int Inherit;
        }
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        private static extern SafeFileHandle CreateFileW(string name, uint access, uint share,
            IntPtr security, uint disposition, uint flags, IntPtr template);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        private static extern bool CreateDirectoryW(string name, ref SecurityAttributes security);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool GetFileInformationByHandle(SafeFileHandle file, out Info info);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        private static extern uint GetFinalPathNameByHandleW(SafeFileHandle file, StringBuilder path,
            uint size, uint flags);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool GetFileInformationByHandleEx(SafeFileHandle file, int kind,
            out StandardInfo info, uint size);
        [DllImport("kernel32.dll", SetLastError=true)]
        private static extern bool SetFileInformationByHandle(SafeFileHandle file, int kind,
            ref byte delete, uint size);
        public static SafeFileHandle OpenPath(string path) {
            // Read metadata only; do not lock out writers, renames or deletions in the source store.
            var h = CreateFileW(path, 0, 7, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero);
            if (h.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
            return h;
        }
        public static void CreatePrivate(string path, byte[] descriptor) {
            var pin = GCHandle.Alloc(descriptor, GCHandleType.Pinned);
            try {
                var security = new SecurityAttributes {
                    Length = Marshal.SizeOf<SecurityAttributes>(), Descriptor = pin.AddrOfPinnedObject()
                };
                if (!CreateDirectoryW(path, ref security)) throw new Win32Exception(Marshal.GetLastWin32Error());
            } finally { pin.Free(); }
        }
        public static SafeFileHandle PinDirectory(string path) {
            var h = CreateFileW(path, 1, 3, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero);
            if (h.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
            return h;
        }
        public static SafeFileHandle OpenForRemoval(string path) {
            var h = CreateFileW(path, 0x10000, 3, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero);
            if (h.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
            return h;
        }
        public static void Remove(SafeFileHandle file) {
            byte delete = 1;
            if (!SetFileInformationByHandle(file, 4, ref delete, 1))
                throw new Win32Exception(Marshal.GetLastWin32Error());
        }
        public static long Allocated(SafeFileHandle file) {
            StandardInfo i;
            if (!GetFileInformationByHandleEx(file, 1, out i, (uint)Marshal.SizeOf<StandardInfo>()))
                throw new Win32Exception(Marshal.GetLastWin32Error());
            return i.AllocationSize;
        }
        public static string[] Inspect(SafeFileHandle file) {
            Info i;
            if (!GetFileInformationByHandle(file, out i)) throw new Win32Exception(Marshal.GetLastWin32Error());
            var path = new StringBuilder(1024);
            uint n = GetFinalPathNameByHandleW(file, path, (uint)path.Capacity, 0);
            if (n == 0 || n >= path.Capacity) throw new Win32Exception(Marshal.GetLastWin32Error());
            return new[] {path.ToString().Substring(4), i.Volume+":"+i.IndexHigh+":"+i.IndexLow,
                i.Links.ToString(), (((ulong)i.SizeHigh<<32)|i.SizeLow).ToString(),
                i.WriteHigh+":"+i.WriteLow, i.Attributes.ToString()};
        }
    }
}
'@
}

$script:StorageOwner = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$script:StorageSystem = [System.Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$script:OrdinaryFlags = [IO.FileAttributes]'ReparsePoint,Device,Offline,SparseFile,Compressed,Encrypted'
$script:MetadataAllowance = 8MB

function Get-StoragePath([string]$path, [switch]$File) {
    $path = [IO.Path]::GetFullPath($path)
    for ($part = $path; $part; $part = [IO.Path]::GetDirectoryName($part)) {
        $attr = [IO.File]::GetAttributes($part)
        if (($attr -band [IO.FileAttributes]'ReparsePoint,Device,Offline') -or
            (($part -ne $path -or -not $File) -and -not ($attr -band [IO.FileAttributes]::Directory))) {
            throw 'Unexpected file type or reparse point in a planned path.'
        }
    }
    $handle = [OllamaStore36.Native]::OpenPath($path)
    try { $meta = [OllamaStore36.Native]::Inspect($handle) } finally { $handle.Dispose() }
    Assert-StorageMetadata $meta $path -File:$File
    return ,$meta
}

function Assert-DefaultStream([string]$path) {
    $streams = @(Get-Item -LiteralPath $path -Stream '*')
    if ($streams.Count -ne 1 -or $streams[0].Stream -ne ':$DATA') { throw 'Unexpected NTFS data stream.' }
}

function Assert-StorageMetadata($meta, [string]$path, [switch]$File) {
    $attr = [IO.FileAttributes][int]$meta[5]
    if ($meta[0] -ne $path -or ($attr -band $script:OrdinaryFlags) -or
        ($File -and (($attr -band [IO.FileAttributes]::Directory) -or [int]$meta[2] -ne 1))) {
        throw 'Unexpected file type, canonical path or link count.'
    }
}

function Assert-PrivateDirectory([string]$path) {
    $null = Get-StoragePath $path
    $acl = Get-Acl -LiteralPath $path
    $rules = $acl.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier])
    $expected = @($script:StorageOwner, $script:StorageSystem)
    if ($acl.GetOwner([System.Security.Principal.SecurityIdentifier]) -ne $script:StorageOwner -or
        $rules.Count -ne 2 -or @($rules.IdentityReference | Select-Object -Unique).Count -ne 2 -or
        ($rules | Where-Object { $_.AccessControlType -ne 'Allow' -or
            $_.IdentityReference -notin $expected -or $_.FileSystemRights -ne 'FullControl' })) {
        throw 'Storage ACL differs from Owner/SYSTEM-only.'
    }
}

function New-PrivateDirectory([string]$path) {
    if (Test-Path -LiteralPath $path) { throw 'Private directory already exists.' }
    $null = Get-StoragePath ([IO.Path]::GetDirectoryName($path))
    $acl = [System.Security.AccessControl.DirectorySecurity]::new()
    $acl.SetOwner($script:StorageOwner)
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($identity in @($script:StorageOwner, $script:StorageSystem)) {
        $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
            $identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
    }
    [OllamaStore36.Native]::CreatePrivate($path, $acl.GetSecurityDescriptorBinaryForm())
    Assert-PrivateDirectory $path
    if (-not (Get-Acl -LiteralPath $path).AreAccessRulesProtected) { throw 'Inherited permissions on stage root.' }
    $meta = Get-StoragePath $path
    return $meta[1]
}

function Add-DirectoryPin($pins, [string]$path) {
    $snapshot = Get-StoragePath $path
    $handle = [OllamaStore36.Native]::PinDirectory($path)
    $pins[$path] = $handle
    $verified = [OllamaStore36.Native]::Inspect($handle)
    Assert-StorageMetadata $verified $path
    if ($snapshot[1] -ne $verified[1]) { throw 'Directory changed while obtaining its handle.' }
}

function Pin-StorageParents($pins, [string]$path) {
    $ordered = [Collections.Generic.Stack[string]]::new()
    for ($part = $path; $part -and [IO.Path]::GetDirectoryName($part); $part = [IO.Path]::GetDirectoryName($part)) {
        $ordered.Push($part)
    }
    foreach ($part in $ordered) { Add-DirectoryPin $pins $part }
}

function Get-AllocatedBound([long]$bytes, [long]$cluster) {
    return [long]([math]::Ceiling($bytes / $cluster) * $cluster)
}

function Read-StorageFile($inputFile, $entry, $buffer, $outputFile, [long]$AllocationLimit = 0) {
    if ($inputFile.Length -ne $entry.bytes) { throw 'File length differs from manifest.' }
    $inputFile.Position = 0
    $sha = [Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $seen = 0L
    try {
        while (($count = $inputFile.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $seen += $count
            if ($seen -gt $entry.bytes) { throw 'File grew during transfer.' }
            $sha.AppendData($buffer, 0, $count)
            if ($outputFile) {
                $outputFile.Write($buffer, 0, $count)
                if ([OllamaStore36.Native]::Allocated($outputFile.SafeFileHandle) -gt $AllocationLimit) {
                    throw 'Actual file allocation exceeded the remaining storage cap.'
                }
            }
            $factor = if ($outputFile) { 2 } else { 1 }
            $waitMs = [math]::Floor(($factor * $seen * 1000.0 / 64MB) - $timer.Elapsed.TotalMilliseconds)
            if ($waitMs -gt 0) { Start-Sleep -Milliseconds $waitMs }
        }
        if ($seen -ne $entry.bytes -or
            [Convert]::ToHexString($sha.GetHashAndReset()) -ine $entry.sha256) { throw 'File SHA-256 hash mismatch.' }
    } finally { $sha.Dispose() }
}

function Remove-OwnedStage([string]$stage, $owned) {
    if (-not $owned.Contains($stage) -or [IO.Path]::GetFileName($stage) -cnotmatch '^\.ollama-stage-[0-9a-f]{32}$') {
        throw 'Unrecognized staging identity. Manual reconciliation required.'
    }
    # First inspect the entire recorded tree. Never traverse an unexpected entry.
    foreach ($path in $owned.Keys) {
        $item = $owned[$path]
        $meta = Get-StoragePath $path -File:(-not $item.directory)
        if ($meta[1] -ne $item.id) { throw 'Stage identity changed. Manual reconciliation required.' }
        if ($item.directory) {
            Assert-PrivateDirectory $path
            foreach ($child in [IO.Directory]::EnumerateFileSystemEntries($path)) {
                if (-not $owned.Contains($child)) { throw 'Unknown staging entry. Manual reconciliation required.' }
            }
        }
    }
    foreach ($path in @($owned.Keys | Sort-Object Length -Descending)) {
        $item = $owned[$path]
        $null = Get-StoragePath $path -File:(-not $item.directory)
        $handle = [OllamaStore36.Native]::OpenForRemoval($path)
        try {
            $meta = [OllamaStore36.Native]::Inspect($handle)
            Assert-StorageMetadata $meta $path -File:(-not $item.directory)
            if ($meta[1] -ne $item.id) { throw 'Stage identity changed. Manual reconciliation required.' }
            [OllamaStore36.Native]::Remove($handle)
        } finally { $handle.Dispose() }
    }
}

function Invoke-OllamaStorageCopy([string]$Source, [string]$Destination, $Entries, [long]$Total,
        [long]$Cap, [long]$Cluster, [scriptblock]$BeforePromote, [switch]$RequireLiveCapacity) {
    $ErrorActionPreference = 'Stop'
    $parent = [IO.Path]::GetDirectoryName($Destination)
    if ([IO.Path]::GetPathRoot($Destination) -ne 'D:\' -or $Cluster -le 0 -or
        $Entries.Count -ne 6 -or @($Entries.path | Sort-Object -Unique).Count -ne 6) { throw 'Invalid copy plan.' }
    for ($i = 0; $i -lt 6; $i++) {
        $e = $Entries[$i]
        if ($e.sha256 -cnotmatch '^[a-f0-9]{64}$' -or $e.bytes -le 0 -or
            ($i -lt 5 -and $e.path -cne "blobs/sha256-$($e.sha256)") -or
            ($i -eq 5 -and $e.path -cnotmatch '^manifests/(?:registry\.ollama\.ai/library/qwen3/)?14b$')) {
            throw 'Invalid allowlisted file.'
        }
    }
    $bound = $script:MetadataAllowance
    foreach ($entry in $Entries) { $bound += Get-AllocatedBound $entry.bytes $Cluster }
    if (($Entries | Measure-Object bytes -Sum).Sum -ne $Total -or $bound -gt $Cap) { throw 'Storage cap or total mismatch.' }
    $parentInfo = Get-StoragePath $parent
    if (Test-Path -LiteralPath $Destination) { throw 'The destination already exists.' }
    $stage = Join-Path $parent ('.ollama-stage-' + [guid]::NewGuid().ToString('N'))
    $owned = [ordered]@{}
    $inputs = [ordered]@{}
    $verified = [ordered]@{}
    $parentPins = [ordered]@{}
    $stagePins = [ordered]@{}
    $baseline = @{}
    $published = $false
    $tracked = $script:MetadataAllowance
    $allocated = $script:MetadataAllowance
    $buffer = [byte[]]::new(1MB)
    try {
        Pin-StorageParents $parentPins $parent
        if ([OllamaStore36.Native]::Inspect($parentPins[$parent])[1] -ne $parentInfo[1]) {
            throw 'Publication parent changed before writing.'
        }
        foreach ($entry in $Entries) {
            $path = Join-Path $Source $entry.path
            $meta = Get-StoragePath $path -File
            Assert-DefaultStream $path
            $reader = [IO.FileStream]::new($path, 'Open', 'Read', 'ReadWrite,Delete')
            $inputs[$entry.path] = $reader
            $open = [OllamaStore36.Native]::Inspect($reader.SafeFileHandle)
            if (($meta -join '|') -ne ($open -join '|')) { throw 'Source moved or changed while opening.' }
            Read-StorageFile $reader $entry $buffer $null
            $baseline[$entry.path] = $open -join '|'
        }
        if ($RequireLiveCapacity -and (Get-Volume -DriveLetter D).SizeRemaining -lt 20GB) {
            throw 'Insufficient free space immediately before writing.'
        }
        $owned[$stage] = @{ id = (New-PrivateDirectory $stage); directory = $true }
        Add-DirectoryPin $stagePins $stage
        foreach ($entry in $Entries) {
            $tracked += Get-AllocatedBound $entry.bytes $Cluster
            if ($tracked -gt $Cap) { throw 'Storage cap reached.' }
            $folder = $stage
            $parts = $entry.path.Split('/')
            foreach ($part in $parts[0..($parts.Count - 2)]) {
                $folder = Join-Path $folder $part
                if (-not $owned.Contains($folder)) {
                    $owned[$folder] = @{ id = (New-PrivateDirectory $folder); directory = $true }
                    Add-DirectoryPin $stagePins $folder
                }
            }
            $path = Join-Path $folder $parts[-1]
            $writer = [IO.FileStream]::new($path, 'CreateNew', 'Write', 'None')
            try {
                $created = [OllamaStore36.Native]::Inspect($writer.SafeFileHandle)
                $owned[$path] = @{ id = $created[1]; directory = $false }
                Assert-StorageMetadata $created $path -File
                Read-StorageFile $inputs[$entry.path] $entry $buffer $writer ($Cap - $allocated)
                $writer.Flush($true)
            } finally { $writer.Dispose() }
            Assert-DefaultStream $path
            # Deny further data writes until just before the directory rename.
            $reader = [IO.FileStream]::new($path, 'Open', 'Read', 'Read,Delete')
            $verified[$path] = $reader
            $reopened = [OllamaStore36.Native]::Inspect($reader.SafeFileHandle)
            Assert-StorageMetadata $reopened $path -File
            if ($reopened[1] -ne $owned[$path].id) { throw 'Staged file identity changed.' }
            $allocated += [OllamaStore36.Native]::Allocated($reader.SafeFileHandle)
            if ($allocated -gt $Cap) { throw 'Actual allocation exceeded the storage cap.' }
            Read-StorageFile $reader $entry $buffer $null
        }
        if ($BeforePromote) { & $BeforePromote }
        foreach ($entry in $Entries) {
            $originalPath = Join-Path $Source $entry.path
            if (((Get-StoragePath $originalPath -File) -join '|') -ne $baseline[$entry.path]) { throw 'Source changed.' }
            Assert-DefaultStream $originalPath
        }
        foreach ($path in $owned.Keys) {
            $item = $owned[$path]
            $meta = Get-StoragePath $path -File:(-not $item.directory)
            if ($meta[1] -ne $item.id) { throw 'Staging identity changed.' }
            if ($item.directory) {
                Assert-PrivateDirectory $path
                foreach ($child in [IO.Directory]::EnumerateFileSystemEntries($path)) {
                    if (-not $owned.Contains($child)) { throw 'Unexpected staging contents.' }
                }
            } else {
                $streamMeta = [OllamaStore36.Native]::Inspect($verified[$path].SafeFileHandle)
                if (($meta -join '|') -ne ($streamMeta -join '|')) { throw 'Staging file metadata changed.' }
                $item.stamp = $streamMeta[1..5] -join '|'
            }
        }
        if ((Get-StoragePath $parent)[1] -ne $parentInfo[1] -or (Test-Path -LiteralPath $Destination)) {
            throw 'Publication parent changed or destination already exists.'
        }
        # NTFS refuses this directory rename while child handles remain open.
        foreach ($handle in $verified.Values) { $handle.Dispose() }
        $verified.Clear()
        foreach ($handle in $stagePins.Values) { $handle.Dispose() }
        $stagePins.Clear()
        [IO.Directory]::Move($stage, $Destination)
        $published = $true
        if ((Get-StoragePath $Destination)[1] -ne $owned[$stage].id) { throw 'Published directory identity changed.' }
        foreach ($entry in $Entries) {
            $before = Join-Path $stage $entry.path
            $finalPath = Join-Path $Destination $entry.path
            $finalMeta = Get-StoragePath $finalPath -File
            if (($finalMeta[1..5] -join '|') -ne $owned[$before].stamp) {
                throw 'Published file metadata changed.'
            }
            Assert-DefaultStream $finalPath
            $reader = [IO.FileStream]::new($finalPath, 'Open', 'Read', 'Read')
            try {
                $opened = [OllamaStore36.Native]::Inspect($reader.SafeFileHandle)
                if (($opened -join '|') -ne ($finalMeta -join '|')) { throw 'Published file changed while opening.' }
                Read-StorageFile $reader $entry $buffer $null
            } finally { $reader.Dispose() }
        }
        foreach ($entry in $Entries) {
            Read-StorageFile $inputs[$entry.path] $entry $buffer $null
            if (((Get-StoragePath (Join-Path $Source $entry.path) -File) -join '|') -ne $baseline[$entry.path]) {
                throw 'Source changed during final validation.'
            }
        }
        [pscustomobject]@{ files = 6; bytes = $Total; allocated_bound = $tracked
            allocated_file_bytes = $allocated - $script:MetadataAllowance; stage_removed = $true }
    } finally {
        foreach ($handle in $inputs.Values) { $handle.Dispose() }
        foreach ($handle in $verified.Values) { $handle.Dispose() }
        foreach ($handle in $stagePins.Values) { $handle.Dispose() }
        try {
            if ($owned.Count -gt 0 -and -not $published) { Remove-OwnedStage $stage $owned }
        } finally { foreach ($handle in $parentPins.Values) { $handle.Dispose() } }
    }
}

function Open-StorageAttempt([string]$parent) {
    return [IO.FileStream]::new((Join-Path $parent '.issue36-copy-attempt'), 'CreateNew', 'Write', 'None')
}

if ($MyInvocation.InvocationName -ne '.') {
    $ErrorActionPreference = 'Stop'
    if ($ApprovalCommentId -le 0) { throw 'Storage Owner approval is required; no model files were opened.' }
    $expected = 'TÔI PHÊ DUYỆT đúng MỘT LẦN sao chép lưu trữ, không chạy AI, cho model qwen3:14b từ kho Ollama Windows hiện có sang kho RIÊNG D:\ProjectData\AIChatBot\ollama-models, giới hạn tối đa 12 GiB dung lượng mới trên ổ D (bao gồm tệp tạm). Chỉ sao chép đúng 1 manifest và 5 blob đã có và đã xác minh SHA-256. Phải kiểm tra SHA-256 đầy đủ ở nguồn trước khi sao chép và tại đích sau khi sao chép; không ghi đè, không sửa nguồn, không tạo bản sao trên ổ C, không động vào Ollama dùng chung. Nếu thiếu điều kiện an toàn hoặc sao chép thất bại, dừng và báo cáo, không tự thử lại. Quyền này KHÔNG cho phép khởi động Ollama, nạp model, dùng GPU hoặc gửi bất kỳ prompt/POST AI nào. Agent Dispatcher, Gate 2 và production tiếp tục NO-GO.'
    $raw = gh api "repos/kha997/ai-chatbot/issues/comments/$ApprovalCommentId"
    if ($LASTEXITCODE -ne 0) { throw 'Unable to verify Issue #36 Owner comment.' }
    $comment = $raw | ConvertFrom-Json
    if ($comment.id -ne $ApprovalCommentId -or $comment.user.node_id -cne 'U_kgDODFyvuQ' -or
        $comment.author_association -cne 'OWNER' -or
        $comment.issue_url -cne 'https://api.github.com/repos/kha997/ai-chatbot/issues/36' -or
        $comment.created_at -ne $comment.updated_at -or
        $comment.body.Trim() -cne $expected) { throw 'Owner comment does not match the exact Issue #36 approval.' }
    $planPath = Join-Path $PSScriptRoot '../docs/OLLAMA_QWEN3_14B_STORAGE_MANIFEST.json'
    $planText = (Get-Content -LiteralPath $planPath -Raw).Replace("`r`n", "`n")
    $planDigest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($planText)))
    if ($planDigest -ine '52debe5e5fa772cc86df634751c505b1b73547cd5fb31e946469cceff442be38') {
        throw 'Immutable model plan digest mismatch.'
    }
    $plan = $planText | ConvertFrom-Json
    $dest = 'D:\ProjectData\AIChatBot\ollama-models'
    if ($plan.model -cne 'qwen3:14b' -or $plan.proposed_windows_store -cne $dest -or
        $plan.total_file_bytes -ne 9276199424 -or $plan.maximum_new_storage_bytes -ne 12GB) { throw 'Unexpected model plan.' }
    $volume = Get-Volume -DriveLetter D
    if ($volume.FileSystem -ne 'NTFS' -or $volume.SizeRemaining -lt 20GB) { throw 'Insufficient free space or unexpected filesystem.' }
    if (Test-Path -LiteralPath $dest) { throw 'The destination already exists.' }
    $parent = [IO.Path]::GetDirectoryName($dest)
    foreach ($dir in @('D:\ProjectData', $parent)) {
        if (-not (Test-Path -LiteralPath $dir)) { $null = New-PrivateDirectory $dir }
        else { $null = Get-StoragePath $dir }
    }
    Assert-PrivateDirectory $parent
    if (@(Get-ChildItem -LiteralPath $parent -Filter '.ollama-stage-*' -Force).Count -gt 0) {
        throw 'A previous stage requires manual reconciliation.'
    }
    $lock = $null
    $approvedPins = [ordered]@{}
    try {
        Pin-StorageParents $approvedPins $parent
        Assert-PrivateDirectory $parent
        $lock = Open-StorageAttempt $parent
        $stamp = [Text.Encoding]::UTF8.GetBytes("Issue #36 Owner comment $ApprovalCommentId reserved with no retry.`n")
        $lock.Write($stamp)
        $lock.Flush($true)
        $entries = @($plan.blobs) + @($plan.source_manifest)
        $profileDir = [Environment]::GetFolderPath('UserProfile')
        if (-not [IO.Path]::IsPathFullyQualified($profileDir)) { throw 'Cannot identify the Windows profile.' }
        $result = Invoke-OllamaStorageCopy (Join-Path $profileDir '.ollama/models') $dest $entries `
            $plan.total_file_bytes $plan.maximum_new_storage_bytes $volume.AllocationUnitSize -RequireLiveCapacity
        $result | Add-Member -NotePropertyName free_bytes_before -NotePropertyValue $volume.SizeRemaining
        $result | Add-Member -NotePropertyName free_bytes_after -NotePropertyValue (Get-Volume -DriveLetter D).SizeRemaining
        if ($result.free_bytes_before - $result.free_bytes_after -gt 12GB) {
            throw 'Observed D: free-space loss exceeds the cap; preserve the destination for reconciliation.'
        }
        $result
    } finally {
        if ($lock) { $lock.Dispose() }
        foreach ($handle in $approvedPins.Values) { $handle.Dispose() }
    }
}
