@echo off
REM Complete Installation Script for mmcli YouTube downloader (Windows)
REM This script installs mmcli globally using pipx

setlocal enabledelayedexpansion

echo === MMCLI Installation Script ===
echo This will install mmcli globally using pipx
echo.

REM Step 1: Check prerequisites
echo Step 1: Checking system prerequisites...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python first.
    echo Download from: https://python.org/downloads/
    pause
    exit /b 1
)

REM Get Python version for verification
for /f "tokens=2" %%a in ('python --version') do set PYTHON_VERSION=%%a
echo ✓ Python %PYTHON_VERSION% found

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip not found! Please ensure pip is installed with Python.
    pause
    exit /b 1
)
echo ✓ pip is available

REM Check if ffmpeg is available
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo WARNING: ffmpeg not found in PATH!
    echo mmcli requires ffmpeg for media conversion.
    echo.
    
    REM Check if chocolatey is available for automatic installation
    choco --version >nul 2>&1
    if not errorlevel 1 (
        echo Chocolatey package manager found!
        set /p install_ffmpeg="Would you like to automatically install ffmpeg via Chocolatey? (y/n): "
        if /i "!install_ffmpeg!"=="y" (
            echo Installing ffmpeg via Chocolatey...
            choco install ffmpeg -y
            if not errorlevel 1 (
                echo ✓ ffmpeg installed successfully via Chocolatey
                echo Please restart your command prompt to use ffmpeg
            ) else (
                echo ERROR: Failed to install ffmpeg via Chocolatey
                echo Please install manually from: https://ffmpeg.org/download.html
            )
        )
    ) else (
        echo Automatic installation options:
        echo 1. Install Chocolatey package manager, then run: choco install ffmpeg
        echo 2. Download from: https://ffmpeg.org/download.html
        echo 3. Use winget ^(Windows 10/11^): winget install ffmpeg
        echo.
        
        REM Check if winget is available
        winget --version >nul 2>&1
        if not errorlevel 1 (
            set /p use_winget="Would you like to try installing via winget? (y/n): "
            if /i "!use_winget!"=="y" (
                echo Installing ffmpeg via winget...
                winget install "FFmpeg (Essentials Build)"
                if not errorlevel 1 (
                    echo ✓ ffmpeg installed successfully via winget
                    echo Please restart your command prompt to use ffmpeg
                ) else (
                    echo WARNING: winget installation failed, you may need to install manually
                )
            )
        )
    )
    
    echo.
    set /p continue="Continue mmcli installation anyway? (y/n): "
    if /i not "!continue!"=="y" exit /b 1
) else (
    echo ✓ ffmpeg is available
)

echo.

REM Step 2: Install pipx if not available
echo Step 2: Checking pipx installation...
pipx --version >nul 2>&1
if errorlevel 1 (
    echo pipx not found, installing...
    pip install --user pipx
    if errorlevel 1 (
        echo ERROR: Failed to install pipx!
        pause
        exit /b 1
    )
    echo ✓ pipx installed successfully
    
    REM Ensure pipx is in PATH
    python -m pipx ensurepath
    echo ✓ pipx PATH configured
    echo.
    echo NOTE: If pipx commands still fail, use 'python -m pipx' instead of 'pipx'
    set PIPX_CMD=python -m pipx
) else (
    echo ✓ pipx is available
    set PIPX_CMD=pipx
)

REM Step 3: Navigate to project root
echo Step 3: Preparing installation...
cd /d "%~dp0.."
if not exist "main.py" (
    echo ERROR: main.py not found! Please run this script from the bin/ directory.
    pause
    exit /b 1
)
echo ✓ Project root located

REM Step 4: Install mmcli globally using pipx
echo Step 4: Installing mmcli globally using pipx...
%PIPX_CMD% install -e .
if errorlevel 1 (
    echo ERROR: Installation failed with %PIPX_CMD%!
    echo Trying alternative method...
    if not "%PIPX_CMD%"=="python -m pipx" (
        python -m pipx install -e .
        if errorlevel 1 (
            echo ERROR: Installation failed with both methods!
            pause
            exit /b 1
        )
    ) else (
        echo Installation failed! Make sure you have restarted your command prompt
        pause
        exit /b 1
    )
)
echo ✓ mmcli installed successfully

REM Step 6: Verify installation
echo Step 6: Verifying installation...
mmcli --version >nul 2>&1
if errorlevel 1 (
    echo Testing with --help instead...
    mmcli --help >nul 2>&1
    if errorlevel 1 (
        echo ERROR: mmcli command not found after installation!
        echo This might be because pipx's bin directory is not in your PATH.
        echo.
        echo SOLUTIONS:
        echo 1. Restart your command prompt and try again
        echo 2. Run: python -m pipx ensurepath
        echo 3. Manually add pipx bin directory to PATH:
        for /f "tokens=*" %%i in ('python -c "import site; print(site.USER_BASE)"') do set USER_BASE=%%i
        echo    Add to PATH: %USER_BASE%\Scripts
        echo.
        pause
        exit /b 1
    )
)
echo ✓ mmcli command is available globally

echo.
echo === Installation Complete! ===
echo.
echo mmcli is now installed and available globally!
echo.
echo Usage examples:
echo   mmcli "https://youtube.com/watch?v=..."
echo   mmcli "https://youtube.com/watch?v=..." --resolution 720 --format mp4
echo   mmcli "https://youtube.com/playlist?list=..." --format mp3 --output-dir "%USERPROFILE%\Music"
echo.
echo Type 'mmcli --help' for full command reference
echo.
echo If mmcli command is not found, restart your command prompt and try again.
echo.
pause