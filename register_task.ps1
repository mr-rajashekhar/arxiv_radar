# Registers ONE scheduled task:
#   ArxivRadar - daily 7:00 AM, repeats every 5 min for 11 hours, via pythonw.exe.
#                Windowless (no pop-ups). Idempotent via state\last_run.json:
#                once today's digest is delivered, every subsequent retry exits
#                in <1s as a silent no-op. No self-disable, no reset task needed.
#
# Run in PowerShell (no elevation needed for current-user tasks):
#   powershell -ExecutionPolicy Bypass -File .\register_task.ps1

$Main      = "ArxivRadar"
$Reset     = "ArxivRadar-Reset"
$ScriptDir = $PSScriptRoot
$PythonW   = "C:\Python314\pythonw.exe"
$RadarPy   = Join-Path $ScriptDir "radar.py"

if (-not (Test-Path $PythonW)) {
    Write-Error "pythonw.exe not found at $PythonW"; exit 1
}
if (-not (Test-Path $RadarPy)) {
    Write-Error "radar.py not found at $RadarPy"; exit 1
}

# ---------- Main task: daily 7 AM + repeat every 5 min for 11h ----------
$mainAction  = New-ScheduledTaskAction -Execute $PythonW -Argument "`"$RadarPy`"" -WorkingDirectory $ScriptDir
$mainTrigger = New-ScheduledTaskTrigger -Daily -At 7:00am
$mainTrigger.Repetition = (New-ScheduledTaskTrigger `
    -Once -At 7:00am `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Hours 11)).Repetition

$mainSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)

Unregister-ScheduledTask -TaskName $Main -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask `
    -TaskName $Main `
    -Description "Daily arxiv digest. 7:00 AM, retry every 5 min for 11h. Windowless via pythonw; idempotent via state\last_run.json." `
    -Action $mainAction `
    -Trigger $mainTrigger `
    -Settings $mainSettings `
    -RunLevel Limited | Out-Null

# ---------- Clean up legacy reset task if present ----------
Unregister-ScheduledTask -TaskName $Reset -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "Registered '$Main' -- daily @ 7:00 AM, retry every 5 min x 132 (11h), via pythonw (silent)."
Write-Host "  Idempotent via state\last_run.json (no self-disable, no reset task)."
Write-Host "  Removed legacy '$Reset' task if it existed."
Write-Host ""
Write-Host "  Manual run:    Start-ScheduledTask -TaskName $Main"
Write-Host "  Status:        Get-ScheduledTaskInfo -TaskName $Main"
Write-Host "  State marker:  $ScriptDir\state\last_run.json"
