Set WshShell = CreateObject("WScript.Shell")
strScript = WScript.ScriptFullName
strDir = Left(strScript, InStrRev(strScript, "\") - 1)
WshShell.CurrentDirectory = strDir
WshShell.Run "pythonw.exe """ & strDir & "\main.py""", 0, False
