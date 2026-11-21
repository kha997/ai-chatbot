param(
    [Parameter(Mandatory)]
    [ValidateSet('Install','Enable','Disable','Uninstall','Status')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
$name = 'AIChatBot-GitHubWatcher'
$description = 'Public GET-only work queue for kha997/ai-chatbot (Issue #5)'
$folder = Join-Path $env:LOCALAPPDATA 'AIChatBotWatcher'
$installed = Join-Path $folder 'github_watcher.py'
$paused = Join-Path $folder 'paused'
$user = [Security.Principal.WindowsIdentity]::GetCurrent()
$python = Get-Command python.exe -CommandType Application |
    Where-Object { $_.Source -notmatch '\\WindowsApps\\' } |
    Select-Object -First 1 -ExpandProperty Source
if (!$python) { throw 'An existing Python executable is required.' }
$task = Get-ScheduledTask -TaskName $name -TaskPath '\' -ErrorAction SilentlyContinue
if ($task) {
    $taskUser = $task.Principal.UserId
    if ($taskUser -match '^S-1-') {
        $taskSid = $taskUser
    } else {
        $taskSid = ([Security.Principal.NTAccount]$taskUser).Translate(
            [Security.Principal.SecurityIdentifier]).Value
    }
    if ($task.Description -cne $description -or
        @($task.Actions).Count -ne 1 -or
        $task.Actions.Execute -ine $python -or
        $task.Actions.WorkingDirectory -or
        $task.Actions.Arguments -cne ('-I "' + $installed + '"') -or
        $taskSid -ne $user.User.Value -or
        $task.Principal.LogonType -ne 'Interactive' -or $task.Principal.RunLevel -ne 'Limited' -or
        @($task.Triggers).Count -ne 1 -or
        $task.Triggers.CimClass.CimClassName -ne 'MSFT_TaskTimeTrigger' -or
        $task.Triggers.Repetition.Interval -ne 'PT30M' -or $task.Triggers.Repetition.Duration -or
        $task.Settings.ExecutionTimeLimit -ne 'PT2M' -or
        $task.Settings.MultipleInstances -ne 'IgnoreNew' -or $task.Settings.WakeToRun) {
        throw 'Task name already belongs to a different or modified configuration.'
    }
}

switch ($Action) {
    'Install' {
        if ($task) { throw 'Already registered. Use Status or Enable.' }
        & $python -I -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
        $source = Join-Path $PSScriptRoot 'github_watcher.py'
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        if (Test-Path -LiteralPath $installed) {
            if ((Get-FileHash -LiteralPath $installed).Hash -ne (Get-FileHash -LiteralPath $source).Hash) {
                throw 'Existing watcher snapshot differs. Review and archive it before replacing.'
            }
        } else {
            Copy-Item -LiteralPath $source -Destination $installed
        }
        New-Item -ItemType File -Path $paused -Force | Out-Null
        $job = New-ScheduledTaskAction -Execute $python -Argument ('-I "' + $installed + '"')
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 30)
        $principal = New-ScheduledTaskPrincipal -UserId $user.Name -LogonType Interactive -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        $settings.Enabled = $false
        Register-ScheduledTask -TaskName $name -TaskPath '\' -Action $job -Trigger $trigger -Principal $principal -Settings $settings -Description $description
    }
    'Enable' {
        if (!$task) { throw 'Install the task first.' }
        $source = Join-Path $PSScriptRoot 'github_watcher.py'
        if ((Get-FileHash -LiteralPath $installed).Hash -ne (Get-FileHash -LiteralPath $source).Hash) {
            throw 'Installed snapshot does not match the reviewed source.'
        }
        Enable-ScheduledTask -InputObject $task
        if (Test-Path -LiteralPath $paused) { Remove-Item -LiteralPath $paused }
    }
    'Disable' {
        if (!$task) { throw 'Task is not registered.' }
        New-Item -ItemType File -Path $paused -Force | Out-Null
        Disable-ScheduledTask -InputObject $task
        if ((Get-ScheduledTask -TaskName $name -TaskPath '\').State -eq 'Running') {
            Stop-ScheduledTask -InputObject $task
        }
    }
    'Uninstall' {
        if (!$task) { return }
        & $PSCommandPath -Action Disable | Out-Null
        Unregister-ScheduledTask -InputObject $task -Confirm:$false
    }
    'Status' {
        if ($task) {
            $info = $task | Get-ScheduledTaskInfo
            [pscustomobject]@{
                TaskName = $task.TaskName
                State = $task.State
                LastRunTime = $info.LastRunTime
                LastTaskResult = $info.LastTaskResult
                NextRunTime = $info.NextRunTime
            }
        }
        if (Test-Path -LiteralPath (Join-Path $folder 'state.json')) {
            Get-Content -LiteralPath (Join-Path $folder 'state.json') -Raw
        }
    }
}
