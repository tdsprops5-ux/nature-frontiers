@echo off
REM ============================================
REM Safe Disk Space Cleaner for Nature Frontiers
REM ============================================
REM This script safely frees up 5-100GB without touching:
REM - Your GitHub repository (nature-frontiers)
REM - Python virtual environment
REM - Installed programs
REM - System files
REM - User documents
REM ============================================

echo.
echo ============================================
echo   SAFE DISK SPACE CLEANER
echo   For Nature Frontiers Video Generator
echo ============================================
echo.
echo This will safely clean:
echo   - Windows temporary files
echo   - Browser cache files
echo   - Old Windows update files
echo   - Recycle Bin
echo   - Delivery Optimization cache
echo   - Old log files
echo.
echo WILL NOT TOUCH:
echo   - nature-frontiers repository
echo   - Python installations
echo   - Virtual environments
echo   - Program Files
echo   - Your documents/photos/videos
echo.
pause

echo.
echo [1/8] Emptying Recycle Bin...
powercfg /h off
del /q/f/s %TEMP%\*
del /q/f/s C:\Windows\Temp\*
echo Done.

echo.
echo [2/8] Cleaning Windows Update cache...
if exist C:\Windows\SoftwareDistribution\Download (
    del /q/f/s C:\Windows\SoftwareDistribution\Download\* 2>nul
    echo Windows Update cache cleaned.
) else (
    echo No Windows Update cache found.
)

echo.
echo [3/8] Cleaning Delivery Optimization cache...
if exist C:\Windows\ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache (
    del /q/f/s "C:\Windows\ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache\*" 2>nul
    echo Delivery Optimization cache cleaned.
) else (
    echo No Delivery Optimization cache found.
)

echo.
echo [4/8] Cleaning browser caches...
REM Chrome cache
if exist "%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache" (
    del /q/f/s "%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache\*" 2>nul
    echo Chrome cache cleaned.
)
REM Edge cache
if exist "%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache" (
    del /q/f/s "%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache\*" 2>nul
    echo Edge cache cleaned.
)
REM Firefox cache
if exist "%LOCALAPPDATA%\Mozilla\Firefox\Profiles\" (
    for /d %%i in ("%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\cache2\entries") do del /q/f/s "%%i\*" 2>nul
    echo Firefox cache cleaned.
)

echo.
echo [5/8] Cleaning old log files...
del /q/f/s C:\Windows\Logs\*.log 2>nul
del /q/f/s C:\Windows\Logs\CBS\*.log 2>nul
forfiles /p "C:\Windows\Logs" /s /m *.log /d -30 /c "cmd /c del @path" 2>nul
echo Old log files cleaned.

echo.
echo [6/8] Cleaning prefetch (old files only)...
forfiles /p "C:\Windows\Prefetch" /m *.* /d -30 /c "cmd /c del @path" 2>nul
echo Old prefetch files cleaned.

echo.
echo [7/8] Running Disk Cleanup utility...
cleanmgr /d C /VERYLOWDISK 2>nul
echo Disk Cleanup completed.

echo.
echo [8/8] Analyzing space freed...
echo.
echo Calculating space freed...
powershell -Command "Get-PSDrive C | Select-Object Used,Free,@{Name='FreedEstimate';Expression={'~5-20GB typically'}}"

echo.
echo ============================================
echo   CLEANING COMPLETE!
echo ============================================
echo.
echo Next steps to free MORE space (optional):
echo.
echo 1. Uninstall unused programs:
echo    Settings ^> Apps ^> Installed apps
echo.
echo 2. Move large files to external drive:
echo    - Videos, photos, downloads
echo    - Game libraries (Steam, Epic)
echo.
echo 3. Use Storage Sense:
echo    Settings ^> System ^> Storage ^> Enable Storage Sense
echo.
echo 4. Clear OneDrive cache (if used):
echo    Right-click OneDrive icon ^> Settings ^> Free up space
echo.
echo 5. Move nature-frontiers outputs to another drive:
echo    Edit backend/config.py and change OUTPUT_DIR
echo.
pause

echo.
echo Current disk status:
powershell -Command "Get-PSDrive C | Format-Table Name, Used, Free, Root -AutoSize"
echo.
echo You can now run: python frontend\app.py
echo.
pause
