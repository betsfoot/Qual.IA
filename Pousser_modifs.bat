@echo off
chcp 65001 >nul
title Qual.IA - Pousser les modifications sur GitHub

cd /d "%~dp0"

echo.
echo  ============================================
echo    Qual.IA - Pousser sur GitHub
echo  ============================================
echo.

REM Vérifier qu'on est bien dans un repo git
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo  [ERREUR] Ce dossier n'est pas un repo Git.
    echo  Place ce fichier .bat a la racine du projet.
    pause
    exit /b 1
)

REM Voir ce qui a change
echo  [1/4] Fichiers modifies :
echo.
git status --short
echo.

REM Verifier qu'il y a bien des changements
git diff --quiet HEAD
if errorlevel 1 goto changements
git diff --cached --quiet
if errorlevel 1 goto changements
git status --porcelain | findstr /R "^??" >nul
if errorlevel 1 (
    echo  [INFO] Aucune modification a pousser. Tout est deja a jour.
    echo.
    pause
    exit /b 0
)

:changements
echo.
set /p MESSAGE="  [2/4] Decris ta modification (en quelques mots) : "

if "%MESSAGE%"=="" (
    echo  [ERREUR] Message vide. Annulation.
    pause
    exit /b 1
)

echo.
echo  [3/4] Ajout et commit des fichiers...
git add .
git commit -m "%MESSAGE%"
if errorlevel 1 (
    echo  [ERREUR] Le commit a echoue. Voir le message au-dessus.
    pause
    exit /b 1
)

echo.
echo  [4/4] Envoi sur GitHub...
git push
if errorlevel 1 (
    echo.
    echo  [ERREUR] Le push a echoue.
    echo  Si une fenetre d'authentification s'ouvre, valide-la.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo    SUCCES ! Les modifications sont en ligne.
echo  ============================================
echo.
echo  L'app sur Streamlit Cloud va se redeployer
echo  automatiquement dans 1-2 minutes.
echo.
echo  Verifie : https://qualia-saas.streamlit.app
echo.
pause
