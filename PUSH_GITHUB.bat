@echo off
cd /d "C:\Users\yadel\Desktop\Projet dev SaaS\projet-qualite-ia"
echo Debut push > push_log.txt 2>&1
git remote remove origin >> push_log.txt 2>&1
git remote add origin "https://betsfoot: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@github.com/betsfoot/Qual.IA.git" >> push_log.txt 2>&1
git add . >> push_log.txt 2>&1
git commit -m "Initial commit - Qual.IA MVP" >> push_log.txt 2>&1
git push -u origin main --force >> push_log.txt 2>&1
echo Fin >> push_log.txt 2>&1
