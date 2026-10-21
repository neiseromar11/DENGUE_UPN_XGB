@echo off
setlocal
cd /d "%~dp0"
if defined DENGUEML_PYTHON (
  "%DENGUEML_PYTHON%" "%~dp0iniciar.py" %*
  goto terminar
)
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 (
  py -3.11 "%~dp0iniciar.py" %*
  goto terminar
)
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
  py -3.12 "%~dp0iniciar.py" %*
  goto terminar
)
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
  "%LocalAppData%\Programs\Python\Python311\python.exe" "%~dp0iniciar.py" %*
  goto terminar
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  "%LocalAppData%\Programs\Python\Python312\python.exe" "%~dp0iniciar.py" %*
  goto terminar
)
python -c "import sys; sys.exit(sys.version_info[:2] not in [(3,11),(3,12)])" >nul 2>&1
if not errorlevel 1 (
  python "%~dp0iniciar.py" %*
  goto terminar
)
echo Instale Python 3.11 o 3.12 de 64 bits desde https://www.python.org/downloads/
echo Active la opcion Add Python to PATH y vuelva a abrir este archivo.
echo Tambien puede definir DENGUEML_PYTHON con la ruta de su python.exe.
pause
exit /b 1
:terminar
set "resultado=%errorlevel%"
if not "%resultado%"=="0" pause
exit /b %resultado%
