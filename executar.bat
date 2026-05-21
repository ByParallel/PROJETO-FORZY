@echo off
setlocal

echo ============================================
echo  Digital TWIN -- Motor Monitor
echo ============================================
echo.

:: Verifica Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    pause
    exit /b 1
)

:: Instala dependencias se necessario
echo [1/3] Verificando dependencias...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo Opcoes de execucao:
echo   1) Com ESP32 real (auto-deteccao de porta)
echo   2) Simulacao (sem hardware)
echo.
set /p OPCAO="Escolha [1/2]: "

if "%OPCAO%"=="2" (
    set READER_CMD=python serial_reader.py --simulate
) else (
    set READER_CMD=python serial_reader.py
)

echo.
echo [2/3] Iniciando leitor serial em segundo plano...
start "Serial Reader" cmd /c "%READER_CMD%"

:: Aguarda o banco inicializar
timeout /t 2 /nobreak >nul

echo [3/3] Iniciando dashboard Streamlit...
echo.
python -m streamlit run 1_Inicio.py --server.port 8501

endlocal
