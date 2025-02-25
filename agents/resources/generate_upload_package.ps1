# Ensure cross-platform compatibility
$isWindowsOS = $false
$isUnixOS = $false

# Check for PowerShell Core first
if (Test-Path variable:\IsWindows) {
    $isWindowsOS = $IsWindows
    $isUnixOS = $IsLinux -or $IsMacOS
} else {
    # Fallback for Windows PowerShell 5.1
    $isWindowsOS = $PSVersionTable.PSEdition -eq 'Desktop' -or $env:OS -like '*Windows*'
    $isUnixOS = $PSVersionTable.Platform -eq 'Unix'
}

# Display OS information
if ($isWindowsOS) {
    Write-Host "Running on Windows"
} elseif ($isUnixOS) {
    Write-Host "Running on Linux or macOS"
} else {
    Write-Error "Unsupported OS"
    exit 1
}

# Ensure we're in the correct directory
$scriptPath = $PSScriptRoot
if ($scriptPath) {
    Set-Location -Path $scriptPath
}

# Get the current directory name for the ZIP file
$projectName = Split-Path -Path (Get-Location) -Leaf

# Publish the .NET project for Linux-x64
Write-Host "`nPublishing .NET project..." -ForegroundColor Cyan
dotnet publish -c Release -r linux-x64 --self-contained false
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to publish .NET project"
    exit 1
}

# Define the output path for the ZIP file using the project name
$outputPath = Join-Path -Path (Get-Location) -ChildPath "$projectName.zip"

# Remove existing zip if it exists
if (Test-Path $outputPath) {
    Remove-Item -Path $outputPath -Force
    Write-Host "Removed existing ZIP file"
}

# Create a ZIP archive
Write-Host "`nCreating ZIP archive..." -ForegroundColor Cyan
$publishPath = "./bin/Release/net8.0/linux-x64/publish"

if (!(Test-Path -Path $publishPath)) {
    Write-Error "Publish directory not found at: $publishPath"
    exit 1
}

try {
    if ($isWindowsOS) {
        # Use Compress-Archive on Windows
        Compress-Archive -Path "$publishPath/*" -DestinationPath $outputPath -Force
    } elseif ($isUnixOS) {
        # Use zip on Linux and macOS
        Push-Location $publishPath
        & zip -r $outputPath *
        if ($LASTEXITCODE -ne 0) {
            throw "zip command failed"
        }
        Pop-Location
    }

    if (Test-Path $outputPath) {
        Write-Host "`nSuccessfully created ZIP archive at: $outputPath" -ForegroundColor Green
    } else {
        throw "ZIP file was not created"
    }
} catch {
    Write-Error "Failed to create ZIP archive: $_"
    exit 1
}

Write-Host "Build and packaging completed successfully!" -ForegroundColor Green