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

REM Verifier si Ollama est accessible
echo Verification d'Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo AVERTISSEMENT: Ollama ne semble pas accessible
    echo Assurez-vous qu'Ollama est demarre
    echo.
)

REM Demarrer l'application
echo Lancement de l'application...
python text_corrector.py

if %errorlevel% neq 0 (
    echo.
    echo ERREUR lors du lancement de l'application
    pause
)