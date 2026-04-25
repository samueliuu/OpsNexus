[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$src = 'c:\trae_project\OpsNexus\软著代码文档.txt'
$dirs = Get-ChildItem -Path 'c:\trae_project\OpsNexus' -Directory | Where-Object { $_.Name -match '软著' }
if ($dirs.Count -eq 0) {
    Write-Output "No matching dir found"
    exit
}
$subdirs = Get-ChildItem -Path $dirs[0].FullName -Directory | Where-Object { $_.Name -match '衡驭' }
if ($subdirs.Count -eq 0) {
    Write-Output "No sub dir found"
    exit
}
$dst = Join-Path $subdirs[0].FullName '衡驭OpsNexus智能服务器运维系统_软著代码文档.txt'
Copy-Item -Path $src -Destination $dst -Force
Write-Output "Copied to: $dst"
