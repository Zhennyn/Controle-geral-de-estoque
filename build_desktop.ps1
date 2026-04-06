$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Remove-FileWithRetry {
	param(
		[Parameter(Mandatory = $true)]
		[string]$Path,
		[int]$MaxAttempts = 8,
		[int]$DelayMs = 500
	)

	if (-not (Test-Path $Path)) {
		return
	}

	for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
		try {
			Remove-Item -Path $Path -Force
			if (-not (Test-Path $Path)) {
				return
			}
		}
		catch {
			if ($attempt -eq $MaxAttempts) {
				throw "Nao foi possivel remover '$Path'. Feche o executavel/antivirus e tente novamente."
			}
		}

		Start-Sleep -Milliseconds $DelayMs
	}
}

Write-Host "[1/3] Instalando dependencias..."
py -3.13 -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha no passo de dependencias." }

Write-Host "[2/3] Instalando PyInstaller..."
py -3.13 -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Falha na instalacao do PyInstaller." }

Write-Host "[2.5/3] Liberando executavel anterior..."
$running = Get-Process -Name "EstoquePro" -ErrorAction SilentlyContinue
if ($running) {
	$running | Stop-Process -Force
	Start-Sleep -Milliseconds 600
}
Remove-FileWithRetry -Path (Join-Path $PSScriptRoot "dist\EstoquePro.exe")

Write-Host "[3/3] Gerando executavel..."
py -3.13 -m PyInstaller --noconfirm --onefile --name EstoquePro --add-data "inventory_app/templates;inventory_app/templates" --add-data "inventory_app/static;inventory_app/static" desktop_app.py
if ($LASTEXITCODE -ne 0) { throw "Falha na geracao do executavel." }

Write-Host "Build concluido. Executavel em dist/EstoquePro.exe"
