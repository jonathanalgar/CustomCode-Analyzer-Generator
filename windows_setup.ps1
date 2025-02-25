# Check for Docker installation
Write-Host "`nCustomCode-Analyzer-Generator Installation"
Write-Host "---------------------------------------------`n"
Write-Host "Checking Docker installation..."
try {
    $dockerVersion = docker --version
    Write-Host "Found: $dockerVersion"
} catch {
    Write-Host "`nDocker not found!" -ForegroundColor Red
    Write-Host "`nPlease install Rancher Desktop:"
    Write-Host "1. Visit: https://rancherdesktop.io/"
    Write-Host "2. Download and install Rancher Desktop"
    Write-Host "3. Run this installation script again"
    Write-Host "`nPress any key to exit..."
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    exit
}

# Get the current username
$username = $env:USERNAME

# Set default installation path
$defaultPath = "C:\Users\$username\CustomCode-Analyzer-Generator"

# Prompt user for installation path
$installPath = Read-Host "Please enter installation path [$defaultPath]"

# Use default path if user hits enter without input
if ([string]::IsNullOrWhiteSpace($installPath)) {
    $installPath = $defaultPath
}

# Create main directory if it doesn't exist
if (!(Test-Path -Path $installPath)) {
    Write-Host "`nCreating installation directory..."
    New-Item -ItemType Directory -Path $installPath | Out-Null
}

# Create generated-solutions subdirectory
$genSolutionsPath = Join-Path $installPath "generated-solutions"
if (!(Test-Path -Path $genSolutionsPath)) {
    Write-Host "Creating generated-solutions directory..."
    New-Item -ItemType Directory -Path $genSolutionsPath | Out-Null
}

# Create main script file with Docker check
$mainScriptPath = Join-Path $installPath "customcode-analyzer-generator.ps1"
$mainScriptContent = @'
# Check for Docker installation and daemon
Write-Host "Checking Docker installation..."
try {
    $dockerVersion = docker --version
    Write-Host "Found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "`nDocker not found!" -ForegroundColor Red
    Write-Host "`nPlease install Rancher Desktop:"
    Write-Host "1. Visit: https://rancherdesktop.io/"
    Write-Host "2. Download and install Rancher Desktop"
    Write-Host "3. Try running this script again"
    Write-Host "`nPress any key to exit..."
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    exit
}

Write-Host "`nChecking if Docker daemon is running..."
try {
    $null = docker info
    Write-Host "Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "`nDocker daemon is not running!" -ForegroundColor Red
    Write-Host "Please start Rancher Desktop and try again"
    Write-Host "`nPress any key to exit..."
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    exit
}

# Perform Docker cleanup to prevent accumulation of old containers and images
Write-Host "`nCleaning up old containers and images..."
try {
    # Stop and remove only containers related to this specific image
    $containers = docker ps -a --filter "ancestor=ghcr.io/jonathanalgar/customcode-analyzer-generator" --format "{{.ID}}"
    if ($containers) {
        Write-Host "Removing old containers from customcode-analyzer-generator..."
        docker rm -f $containers
    } else {
        Write-Host "No old containers from customcode-analyzer-generator found."
    }
    
    # Remove only dangling images related to this specific repository
    $danglingImages = docker images --filter "dangling=true" --filter "reference=ghcr.io/jonathanalgar/customcode-analyzer-generator*" --format "{{.ID}}"
    if ($danglingImages) {
        Write-Host "Removing dangling images from customcode-analyzer-generator..."
        docker rmi $danglingImages
    } else {
        Write-Host "No dangling images from customcode-analyzer-generator found."
    }
    
    # Remove old versions of the image (keep the latest)
    $images = docker images "ghcr.io/jonathanalgar/customcode-analyzer-generator" --format "{{.ID}}" | Select-Object -Skip 1
    if ($images) {
        Write-Host "Removing old image versions of customcode-analyzer-generator..."
        docker rmi $images
    } else {
        Write-Host "No old image versions of customcode-analyzer-generator found."
    }
    
    Write-Host "Cleanup completed successfully" -ForegroundColor Green
} catch {
    Write-Host "Warning: Cleanup encountered an issue. Continuing..." -ForegroundColor Yellow
    Write-Host $_.Exception.Message
}

$scriptPath = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
Set-Location -Path $scriptPath

Write-Host "`nChecking for updates..."
docker pull ghcr.io/jonathanalgar/customcode-analyzer-generator:latest

Write-Host "`nRunning..."
docker run -it --rm `
    --env-file .env `
    -v "${PWD}/generated-solutions:/app/output" `
    ghcr.io/jonathanalgar/customcode-analyzer-generator:latest generate

# Wait a moment to make sure any file operations are complete
Start-Sleep -Seconds 1

# After docker completes, check generated solutions directory
$solutionDirs = Get-ChildItem -Path "${PWD}/generated-solutions" -Directory | Sort-Object LastWriteTime -Descending
$mostRecentSolution = $solutionDirs | Select-Object -First 1

if ($mostRecentSolution) {
    $solutionFullPath = $mostRecentSolution.FullName
    $recentTimeThreshold = (Get-Date).AddMinutes(-1)
    
    # Only offer to open solutions created in the last 1 minutes
    if ($mostRecentSolution.LastWriteTime -gt $recentTimeThreshold) {
        # Paths to common development tools
        $vsCodePath = "C:\Users\$env:USERNAME\AppData\Local\Programs\Microsoft VS Code\Code.exe"
        $vsProPath = "C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\IDE\devenv.exe"
        $vsCommunityPath = "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\devenv.exe"
        $vsEnterprisePath = "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\devenv.exe"
        
        $vsPathsToCheck = @($vsProPath, $vsCommunityPath, $vsEnterprisePath)
        $installedVSPath = $vsPathsToCheck | Where-Object { Test-Path -Path $_ -PathType Leaf } | Select-Object -First 1
        
        Write-Host "`nSolution generated successfully at: $solutionFullPath" -ForegroundColor Green
        Write-Host "`nWhat would you like to do?"
        Write-Host "1. Open in VS Code" -ForegroundColor Cyan
        if ($installedVSPath) {
            $vsEdition = if ($installedVSPath -eq $vsProPath) { "Professional" } 
                         elseif ($installedVSPath -eq $vsCommunityPath) { "Community" } 
                         else { "Enterprise" }
            Write-Host "2. Open in Visual Studio $vsEdition" -ForegroundColor Cyan
        }
        Write-Host "3. Open in File Explorer" -ForegroundColor Cyan
        Write-Host "4. Exit" -ForegroundColor Cyan
        
        $choice = Read-Host "`nEnter your choice (1-4)"
        
        switch ($choice) {
            "1" {
                try {
                    if (Test-Path -Path $vsCodePath -PathType Leaf) {
                        Start-Process -FilePath $vsCodePath -ArgumentList "$solutionFullPath" -ErrorAction Stop
                    } else {
                        # Try using 'code' command in case it's in PATH
                        Set-Location -Path $solutionFullPath
                        Start-Process -FilePath "code" -ArgumentList "." -ErrorAction Stop
                    }
                    Write-Host "Opening solution in VS Code..." -ForegroundColor Green
                } catch {
                    Write-Host "`nFailed to open VS Code. You can manually open the solution at: $solutionFullPath" -ForegroundColor Yellow
                }
            }
            "2" {
                if ($installedVSPath) {
                    try {
                        # Find .sln file
                        $slnFile = Get-ChildItem -Path $solutionFullPath -Filter "*.sln" | Select-Object -First 1
                        if ($slnFile) {
                            Start-Process -FilePath $installedVSPath -ArgumentList "`"$($slnFile.FullName)`"" -ErrorAction Stop
                            Write-Host "Opening solution in Visual Studio $vsEdition..." -ForegroundColor Green
                        } else {
                            Start-Process -FilePath $installedVSPath -ArgumentList "$solutionFullPath" -ErrorAction Stop
                            Write-Host "Opening directory in Visual Studio $vsEdition..." -ForegroundColor Green
                        }
                    } catch {
                        Write-Host "`nFailed to open Visual Studio. You can manually open the solution at: $solutionFullPath" -ForegroundColor Yellow
                    }
                } else {
                    Write-Host "`nVisual Studio not found. You can manually open the solution at: $solutionFullPath" -ForegroundColor Yellow
                }
            }
            "3" {
                try {
                    Start-Process -FilePath "explorer.exe" -ArgumentList "$solutionFullPath" -ErrorAction Stop
                    Write-Host "Opening solution in File Explorer..." -ForegroundColor Green
                } catch {
                    Write-Host "`nFailed to open File Explorer. You can manually navigate to: $solutionFullPath" -ForegroundColor Yellow
                }
            }
            "4" {
                Write-Host "`nYou can manually open the solution later at: $solutionFullPath" -ForegroundColor Cyan
            }
            default {
                Write-Host "`nInvalid choice. You can manually open the solution at: $solutionFullPath" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host "`n+----------------------------------------+"
Write-Host "|        Give feedback / Get help:       |"
Write-Host "|         https://bit.ly/4jYWEKU         |"
Write-Host "|                                        |"
Write-Host "|             Thank you! -ja             |"
Write-Host "+----------------------------------------+"

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
'@
Set-Content -Path $mainScriptPath -Value $mainScriptContent

# Prompt for API keys
Write-Host "Please enter your API keys (you can edit these later in the generated .env file)"
$openaiKey = Read-Host "OpenAI API key (required - get one for free at https://platform.openai.com)"
$freepikKey = Read-Host "Freepik API key (optional for icons - get one for free at https://www.freepik.com/api)"
$langchainKey = Read-Host "LangChain API key (optional for tracing - get one for free at https://smith.langchain.com)"

# Function to clean API keys
function Clean-ApiKey {
    param([string]$key)
    # Remove any whitespace, newlines, or carriage returns
    $cleaned = $key.Trim() -replace '[\r\n\s]', ''
    return $cleaned
}

# Create .env file
$envPath = Join-Path $installPath ".env"
$cleanedOpenAiKey = Clean-ApiKey $openaiKey
$cleanedFreepikKey = Clean-ApiKey $freepikKey
$cleanedLangchainKey = Clean-ApiKey $langchainKey

# Build environment variables line by line to ensure proper formatting
$envLines = @()
$envLines += "OPENAI_API_KEY=$cleanedOpenAiKey"
$envLines += "FREEPIK_API_KEY=$cleanedFreepikKey"

# Add Langchain configuration if API key is provided
if (-not [string]::IsNullOrWhiteSpace($cleanedLangchainKey)) {
    $envLines += "LANGCHAIN_API_KEY=$cleanedLangchainKey"
    $envLines += "LANGCHAIN_TRACING_V2=true"
}

$envLines += "RETAIN_ON_FAILURE="
$envLines += "SEARCH_TERM_LLM="
$envLines += "CODE_GENERATION_LLM="

# Join the lines with proper newline characters
$envContent = $envLines -join "`n"

# Write file with UTF8 encoding without BOM
$utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($envPath, $envContent, $utf8NoBomEncoding)

# Write file with UTF8 encoding without BOM
$utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($envPath, $envContent, $utf8NoBomEncoding)

Write-Host "`nInstallation Complete!"
Write-Host "-------------------------"
Write-Host "Installation path: $installPath"
Write-Host "Main script: $mainScriptPath"
Write-Host "Environment file: $envPath"
Write-Host "`nYou can edit the API keys later in the generated .env file. When editing:"
Write-Host "- Ensure each API key is on its own line"
Write-Host "- Do not add spaces around the = sign"
Write-Host "- Do not add quotes around the API keys"
Write-Host "- Do not add comments in the file"
Write-Host "`nTo run the CustomCode-Analyzer-Generator:"
Write-Host "1. Open PowerShell"
Write-Host "2. Navigate to the installation directory:"
Write-Host "   cd `"$installPath`""
Write-Host "3. Run the script:"
Write-Host "   .\customcode-analyzer-generator.ps1"

$effectivePolicy = Get-ExecutionPolicy -Scope Process
if ($effectivePolicy -eq "Undefined") {
    $effectivePolicy = Get-ExecutionPolicy -Scope CurrentUser
}
if ($effectivePolicy -eq "Restricted" -or $effectivePolicy -eq "AllSigned") {
    Write-Host "`nPowerShell is blocking script execution!" -ForegroundColor Yellow
    Write-Host "Detected Execution Policy: $effectivePolicy"
    Write-Host "`nTo allow the script to run, choose one of these two options:"
    Write-Host "   - (Recommended) Change policy to allow local scripts:"
    Write-Host "     Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
    Write-Host "   - (One-time use) Run the script with temporary permission:"
    Write-Host "     powershell -ExecutionPolicy Bypass -File .\customcode-analyzer-generator.ps1"
    Write-Host "`nAfter fixing the execution policy, return to Step 3 and run the script."
}

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')