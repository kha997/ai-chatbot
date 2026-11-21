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
$task = Get-ScheduledTask -TaskName $name -TaskPath '\' -ErrorAction SilentlyContinue
if ($task -and ($task.Description -cne $description -or
    @($task.Actions).Count -ne 1 -or
    $task.Actions.Arguments -cne ('-I "' + $installed + '"'))) {
    throw 'Task name already belongs to a different configuration.'
}

switch ($Action) {
    'Install' {
        if ($task) { throw 'Already registered. Use Status or Enable.' }
        $python = (Get-Command python.exe -CommandType Application).Source
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
        $job = New-ScheduledTaskAction -Execute $python -Argument ('-I "' + $installed + '"') -WorkingDirectory $folder
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(30) -RepetitionInterval (New-TimeSpan -Minutes 30)
        $user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -Disabled -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
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
            $task | Select-Object TaskName, State
            $task | Get-ScheduledTaskInfo | Select-Object LastRunTime, LastTaskResult, NextRunTime
        }
        if (Test-Path -LiteralPath (Join-Path $folder 'state.json')) {
            Get-Content -LiteralPath (Join-Path $folder 'state.json') -Raw
        }
    }
}
