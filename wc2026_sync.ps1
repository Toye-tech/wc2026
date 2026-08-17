$pythonExe = "C:\Users\Admin\Downloads\wc2026_project\wc2026\.venv\Scripts\python.exe"
$projectDir = "C:\Users\Admin\Downloads\wc2026_project\wc2026"

Set-Location $projectDir

while ($true) {
    Write-Host "$(Get-Date) — running fetch_buzz_news..."
    & $pythonExe manage.py fetch_buzz_news

    Write-Host "$(Get-Date) — running fetch_football_data..."
    & $pythonExe manage.py fetch_football_data

    Write-Host "Sleeping 30 minutes..."
    Start-Sleep -Seconds 1800
}
