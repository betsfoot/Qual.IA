@echo off
chcp 65001 >nul
echo ========================================
echo   Publication Qual.IA sur GitHub
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] Initialisation du dépôt Git...
git init -b main
git config user.email "yadelyohann27@gmail.com"
git config user.name "betsfoot"

echo.
echo [2/4] Ajout des fichiers (sauf données sensibles)...
git add .
git status --short

echo.
echo [3/4] Commit...
git commit -m "Initial commit — Qual.IA MVP v1.1"

echo.
echo [4/4] Publication sur GitHub...
git remote remove origin 2>nul
git remote add origin "https://betsfoot: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@github.com/betsfoot/Qual.IA.git"
git push -u origin main --force

echo.
echo ========================================
echo   TERMINÉ ! Le code est sur GitHub.
echo   Supprime ce fichier .bat maintenant.
echo ========================================
pause
