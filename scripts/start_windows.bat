@echo off
echo Demarrage du Correcteur de Texte...
echo.

REM Verifier si Python est installe
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas installe ou pas dans le PATH
    echo Telechargez Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Demarrer l'application
echo Lancement de l'application...
python -m typozap

if %errorlevel% neq 0 (
    echo.
    echo ERREUR lors du lancement de l'application
    pause
)
