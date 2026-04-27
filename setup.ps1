param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

function Get-PythonVersion {
    param([string]$Command)
    try {
        $version = & $Command -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
        return $version.Trim()
    }
    catch {
        return $null
    }
}

function Test-CompatiblePython {
    param([string]$Version)
    if (-not $Version) {
        return $false
    }
    $parts = $Version.Split(".")
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    return ($major -eq 3 -and $minor -ge 10 -and $minor -lt 14)
}

function Find-CompatiblePython {
    $candidates = @()

    if ($PythonPath) {
        $candidates += $PythonPath
    }

    $localAppData = $env:LOCALAPPDATA
    $programFiles = $env:ProgramFiles
    $windowsApps = "$localAppData\Microsoft\WindowsApps"

    $candidates += @(
        "$localAppData\Python\pythoncore-3.13-64\python.exe",
        "$localAppData\Python\pythoncore-3.12-64\python.exe",
        "$localAppData\Programs\Python\Python313\python.exe",
        "$localAppData\Programs\Python\Python312\python.exe",
        "$programFiles\Python313\python.exe",
        "$programFiles\Python312\python.exe",
        "$windowsApps\python3.13.exe",
        "$windowsApps\python3.12.exe",
        "python"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -match "\\|/" -and -not (Test-Path $candidate)) {
            continue
        }

        $version = Get-PythonVersion $candidate
        if ($version) {
            Write-Host "Python candidat: $candidate ($version)"
            if (Test-CompatiblePython $version) {
                return @{
                    Command = $candidate
                    Version = $version
                }
            }
        }
    }

    return $null
}

function Find-PythonManager {
    $localAppData = $env:LOCALAPPDATA
    $candidates = @(
        "$localAppData\Microsoft\WindowsApps\py.exe",
        "$localAppData\Microsoft\WindowsApps\pymanager.exe",
        "py",
        "pymanager"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -match "\\|/" -and -not (Test-Path $candidate)) {
            continue
        }

        try {
            & $candidate list -f *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        }
        catch {
        }
    }

    return $null
}

$python = Find-CompatiblePython

if (-not $python) {
    $manager = Find-PythonManager

    if ($manager) {
        Write-Host ""
        Write-Host "Aucun Python compatible deja installe. Python Manager detecte: $manager"
        Write-Host "Installation automatique de Python 3.13..."
        & $manager install -y 3.13
        $python = Find-CompatiblePython
    }

    if (-not $python) {
        Write-Host ""
        Write-Host "Aucun Python compatible trouve." -ForegroundColor Red
        Write-Host "Le Python actuel pointe probablement vers 3.14, qui force pygame a compiler depuis les sources."
        Write-Host ""
        Write-Host "Installe Python 3.13 depuis python.org, puis relance:"
        Write-Host "  .\setup.ps1"
        Write-Host ""
        Write-Host "Si Python 3.13 est installe mais pas detecte, utilise son chemin complet:"
        Write-Host '  .\setup.ps1 -PythonPath "C:\Users\amaur\AppData\Local\Programs\Python\Python313\python.exe"'
        Write-Host ""
        Write-Host "Note: comme .venv n'a pas ete cree, cette commande ne peut pas marcher pour l'instant:"
        Write-Host "  .\.venv\Scripts\Activate.ps1"
        exit 1
    }
}

Write-Host ""
Write-Host "Python retenu: $($python.Command) ($($python.Version))" -ForegroundColor Green

if (Test-Path ".venv") {
    Write-Host ".venv existe deja. Suppression..."
    Remove-Item -Recurse -Force ".venv"
}

& $python.Command -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host ""
Write-Host "Installation terminee." -ForegroundColor Green
Write-Host "Lancer avec:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python main.py"
