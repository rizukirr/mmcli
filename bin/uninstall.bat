@echo off
REM Complete Uninstallation Script for mmcli YouTube downloader (Windows)
REM This script removes mmcli that was installed globally using pipx

setlocal enabledelayedexpansion

echo === MMCLI Uninstallation Script ===
echo This will remove mmcli that was installed globally using pipx
echo.

REM Step 1: Check if pipx is available
echo Step 1: Checking pipx installation...
pipx --version >nul 2>&1
if errorlevel 1 (
    REM Check if Python is available to use pipx module
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python not found! Cannot proceed with uninstallation.
        echo pipx might not be available to uninstall mmcli
        pause
        exit /b 1
    )
    
    REM Check if pipx module is available
    python -m pipx --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: pipx not found! mmcli might not have been installed via pipx.
        echo If mmcli was installed differently, please remove it manually.
        pause
        exit /b 1
    )
    
    echo WARNING: pipx command not found, using Python module
    set PIPX_CMD=python -m pipx
) else (
    echo ✓ pipx is available
    set PIPX_CMD=pipx
)

echo.

REM Step 2: Check if mmcli is currently installed
echo Step 2: Checking if mmcli is installed...
%PIPX_CMD% list | findstr "mmcli" >nul 2>&1
if errorlevel 1 (
    echo WARNING: mmcli not found in pipx installations
    
    REM Check if mmcli command is still available
    mmcli --help >nul 2>&1
    if not errorlevel 1 (
        echo WARNING: mmcli command found but not in pipx list
        echo mmcli might have been installed via a different method
        echo.
        set /p continue="Continue anyway to attempt removal? (y/n): "
        if /i not "!continue!"=="y" exit /b 0
    ) else (
        echo INFO: mmcli is not currently installed
        pause
        exit /b 0
    )
) else (
    echo ✓ mmcli found in pipx installations
)

echo.

REM Step 3: Uninstall mmcli
echo Step 3: Uninstalling mmcli...
%PIPX_CMD% uninstall mmcli
if errorlevel 1 (
    echo ERROR: Failed to uninstall mmcli with %PIPX_CMD%!
    echo Trying alternative method...
    if not "%PIPX_CMD%"=="python -m pipx" (
        python -m pipx uninstall mmcli
        if errorlevel 1 (
            echo ERROR: Uninstallation failed with both methods!
            pause
            exit /b 1
        )
    ) else (
        echo ERROR: Uninstallation failed!
        pause
        exit /b 1
    )
)
echo ✓ mmcli uninstalled successfully

echo.

REM Step 4: Verify removal
echo Step 4: Verifying removal...
mmcli --help >nul 2>&1
if not errorlevel 1 (
    echo WARNING: mmcli command is still available
    echo This might indicate:
    echo   - mmcli was installed in multiple ways
    echo   - PATH cache needs to be refreshed
    echo   - Different installation method was used
    echo.
    echo Try restarting your command prompt and check again
) else (
    echo ✓ mmcli command is no longer available
)

REM Step 5: Optional cleanup
echo.
echo Step 5: Optional cleanup...

REM Ask about ffmpeg removal
ffmpeg -version >nul 2>&1
if not errorlevel 1 (
    echo.
    set /p remove_ffmpeg="Would you like to remove ffmpeg as well? (y/n): "
    if /i "!remove_ffmpeg!"=="y" (
        echo Attempting to remove ffmpeg...
        
        REM Check if chocolatey is available
        choco --version >nul 2>&1
        if not errorlevel 1 (
            choco list --local-only | findstr "ffmpeg" >nul 2>&1
            if not errorlevel 1 (
                echo Removing ffmpeg via Chocolatey...
                choco uninstall ffmpeg -y
                if not errorlevel 1 (
                    echo ✓ ffmpeg removed successfully via Chocolatey
                ) else (
                    echo ERROR: Failed to remove ffmpeg via Chocolatey
                )
            ) else (
                echo INFO: ffmpeg not installed via Chocolatey
            )
        ) else (
            REM Check if winget is available
            winget --version >nul 2>&1
            if not errorlevel 1 (
                echo Attempting to remove ffmpeg via winget...
                winget uninstall ffmpeg
                if not errorlevel 1 (
                    echo ✓ ffmpeg removed successfully via winget
                ) else (
                    echo WARNING: winget removal failed or ffmpeg not installed via winget
                )
            ) else (
                echo WARNING: Cannot automatically remove ffmpeg on this system
                echo Please remove ffmpeg manually:
                echo 1. If installed via Chocolatey: choco uninstall ffmpeg
                echo 2. If installed via winget: winget uninstall ffmpeg
                echo 3. If installed manually: Remove from installation directory and PATH
            )
        )
    )
) else (
    echo INFO: ffmpeg not found in PATH
)

echo.
set /p remove_pipx="Would you like to remove pipx if it's no longer needed? (y/n): "
if /i "!remove_pipx!"=="y" (
    REM Check if pipx has any other packages
    %PIPX_CMD% list | findstr "package" >nul 2>&1
    if not errorlevel 1 (
        echo INFO: pipx has other packages installed, keeping pipx
        %PIPX_CMD% list
    ) else (
        echo Removing pipx...
        if "%PIPX_CMD%"=="pipx" (
            pip uninstall -y pipx
        ) else (
            python -m pip uninstall -y pipx
        )
        echo ✓ pipx removed
    )
)

echo.
echo === Uninstallation Complete! ===
echo.
echo mmcli has been successfully removed from your system!
echo.
echo If you want to reinstall mmcli later, run:
echo   bin\install.bat
echo.
echo Thank you for using mmcli!
echo.
pause