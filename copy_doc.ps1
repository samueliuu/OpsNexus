$src = 'c:\trae_project\OpsNexus\软著代码文档.txt'
$dir = Get-ChildItem 'c:\trae_project\OpsNexus\软著资料' | Where-Object { $_.Name -like '*衡驭*' -and $_.PSIsContainer } | Select-Object -First 1
$dst = Join-Path $dir.FullName '衡驭OpsNexus智能服务器运维系统_软著代码文档.txt'
Copy-Item -Path $src -Destination $dst -Force
Write-Output "Copied to: $dst"
