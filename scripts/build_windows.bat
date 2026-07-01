@echo off
echo ========================================
echo    TypoZap - Build Script
echo ========================================
echo.

echo [1/4] Creation de l'icone...
python scripts\create_icon.py
if %errorlevel% neq 0 (
    echo ERREUR: Impossible de creer l'icone
    pause
    exit /b 1
)
echo.

echo [2/4] Installation des dependances...
python -m pip install -e . pyinstaller pillow
if %errorlevel% neq 0 (
    echo ERREUR: Impossible d'installer PyInstaller
    pause
    exit /b 1
)
echo.

echo [3/4] Compilation de l'executable...
python -m PyInstaller packaging\typozap.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo ERREUR: Echec de la compilation
    pause
    exit /b 1
)
echo.

echo [4/4] Nettoyage...
if exist build rmdir /s /q build
echo.

echo ========================================
echo    Build termine avec succes !
echo    Executable: dist\TypoZap.exe
echo ========================================
echo.

pause
