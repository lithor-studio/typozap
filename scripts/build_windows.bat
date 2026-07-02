@echo off
cd /d "%~dp0.."
if %errorlevel% neq 0 (
    echo ERREUR: Impossible d'acceder a la racine du projet
    pause
    exit /b 1
)

echo ========================================
echo    TypoZap - Build Script
echo ========================================
echo.

echo [1/5] Installation des dependances...
python -m pip install --no-build-isolation -e . pyinstaller pillow
if %errorlevel% neq 0 (
    echo AVERTISSEMENT: Installation en ligne impossible, tentative avec les dependances existantes...
    python -c "import PyInstaller, PIL, PyQt5, requests, pyautogui, pynput"
    if %errorlevel% neq 0 (
        echo ERREUR: Des dependances manquent et la connexion a PyPI est indisponible.
        echo Verifiez votre connexion DNS puis relancez ce script.
        pause
        exit /b 1
    )
)
echo.

echo [2/5] Creation de l'icone...
python scripts\create_icon.py
if %errorlevel% neq 0 (
    echo ERREUR: Impossible de creer l'icone
    pause
    exit /b 1
)
echo.

echo [3/5] Recuperation du moteur local...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\download_windows_runtime.ps1
if %errorlevel% neq 0 (
    echo ERREUR: Impossible de recuperer le runtime llama.cpp
    pause
    exit /b 1
)
if not exist runtime\typozap-engine.exe (
    echo ERREUR: runtime\typozap-engine.exe est absent
    pause
    exit /b 1
)
echo.

echo [4/5] Compilation de l'executable...
python -m PyInstaller packaging\typozap.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo ERREUR: Echec de la compilation
    pause
    exit /b 1
)
echo.

echo [5/5] Nettoyage...
if exist build rmdir /s /q build
echo.

echo ========================================
echo    Build termine avec succes !
echo    Executable: dist\TypoZap.exe
echo ========================================
echo.

pause
