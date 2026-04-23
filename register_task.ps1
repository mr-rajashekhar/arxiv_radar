# Registers TWO scheduled tasks:
#   1. ArxivRadar        - daily 7:00 AM, repeats every 5 min for 3 hours
#                          (radar.py self-disables after successful run)
#   2. ArxivRadar-Reset  - daily 6:59 AM, re-enables ArxivRadar for the day
#
# Run in PowerShell (no elevation needed for current-user tasks):
#   powershell -ExecutionPolicy Bypass -File .\register_task.ps1

$Main  = "ArxivRadar"
$Reset = "ArxivRadar-Reset"
$BatPath = Join-Path $PSScriptRoot "run_radar.bat"

if (-not (Test-Path $BatPath)) {
    Write-Error "run_radar.bat not found at $BatPath"; exit 1
}

# ---------- Main task: daily 7 AM + repeat every 5 min for 3h ----------
$mainAction  = New-ScheduledTaskAction -Execute $BatPath -WorkingDirectory $PSScriptRoot
$mainTrigger = New-ScheduledTaskTrigger -Daily -At 7:00am
$mainTrigger.Repetition = (New-ScheduledTaskTrigger `
    -Once -At 7:00am `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Hours 3)).Repetition

$mainSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

Unregister-ScheduledTask -TaskName $Main -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask `
    -TaskName $Main `
    -Description "Daily arxiv digest. Starts 7:00 AM, retries every 5 min for 3h. Self-disables after success." `
    -Action $mainAction `
    -Trigger $mainTrigger `
    -Settings $mainSettings `
    -RunLevel Limited | Out-Null

# ---------- Reset task: daily 6:59 AM, re-enables main ----------
# NOTE: needs Task Scheduler right to modify '$Main'. Current-user task modifying
# another current-user task works without elevation.
$resetCmd = "schtasks /Change /TN `"$Main`" /ENABLE"
$resetAction  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $resetCmd"
$resetTrigger = New-ScheduledTaskTrigger -Daily -At 6:59am
$resetSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

Unregister-ScheduledTask -TaskName $Reset -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask `
    -TaskName $Reset `
    -Description "Re-enables ArxivRadar daily at 6:59 AM (in case it self-disabled yesterday after success)." `
    -Action $resetAction `
    -Trigger $resetTrigger `
    -Settings $resetSettings `
    -RunLevel Limited | Out-Null

Write-Host "Registered '$Main'  -- daily @ 7:00 AM, retry every 5 min x 36 (3h)."
Write-Host "  Self-disables after a successful run."
Write-Host "Registered '$Reset' -- daily @ 6:59 AM, re-enables '$Main'."
Write-Host ""
Write-Host "  Manual run:    Start-ScheduledTask -TaskName $Main"
Write-Host "  Status:        Get-ScheduledTaskInfo -TaskName $Main"
Write-Host "  State marker:  $PSScriptRoot\state\last_run.json"
