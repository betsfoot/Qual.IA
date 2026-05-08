@echo off
title IA Qualite - Demarrage

echo.
echo  ============================================
echo   IA Qualite - Lancement de l'application
echo  ============================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo  ERREUR : Python n est pas installe ou pas dans le PATH.
    echo  Installez Python depuis https://python.org et relancez.
    pause
    exit /b 1
)

if not exist ".env" (
    echo  ERREUR : Fichier .env manquant.
    echo  Copiez .env.example en .env et renseignez votre cle API Anthropic.
    pause
    exit /b 1
)

echo  Verification des dependances...
pip install -r requirements.txt --quiet --disable-pip-version-check

echo.
echo  Demarrage de l application...
echo  Ouvrez votre navigateur sur : http://localhost:8501
echo.
echo  Pour arreter : fermez cette fenetre ou appuyez sur Ctrl+C
echo.

python -m streamlit run frontend/app.py --server.headless false --browser.gatherUsageStats false

echo.
echo  L application s est arretee.
pause
