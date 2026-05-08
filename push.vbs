Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = "C:\Users\yadel\Desktop\Projet dev SaaS\projet-qualite-ia"
oShell.Run "cmd /c PUSH_GITHUB.bat", 0, True
MsgBox "Push GitHub terminé ! Vérifiez push_log.txt pour le résultat.", 64, "Qual.IA"
