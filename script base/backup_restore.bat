@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

title E-Market Express - Utilidad de Backup y Restore (MariaDB / XAMPP)

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "BACKUP_DIR=%SCRIPT_DIR%\backups"
set "DB_NAME=parcial"
set "DB_HOST=localhost"
set "DB_PORT=3306"

:: Localizar binarios de MariaDB / MySQL (XAMPP por defecto o PATH)
set "MYSQLDUMP_BIN=C:\xampp\mysql\bin\mysqldump.exe"
set "MYSQL_BIN=C:\xampp\mysql\bin\mysql.exe"

if not exist "%MYSQLDUMP_BIN%" (
    for /f "delims=" %%I in ('where mysqldump 2^>nul') do set "MYSQLDUMP_BIN=%%I"
)
if not exist "%MYSQL_BIN%" (
    for /f "delims=" %%I in ('where mysql 2^>nul') do set "MYSQL_BIN=%%I"
)

if not exist "%MYSQLDUMP_BIN%" (
    echo [ERROR] No se encontro mysqldump.exe en C:\xampp\mysql\bin ni en el PATH.
    pause
    exit /b 1
)
if not exist "%MYSQL_BIN%" (
    echo [ERROR] No se encontro mysql.exe en C:\xampp\mysql\bin ni en el PATH.
    pause
    exit /b 1
)

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Configuracion predeterminada de conexion (root sin clave en XAMPP)
set "DB_USER=root"
set "DB_PASS="

:: Soporte rapido por linea de comandos:
::   backup_restore.bat backup
::   backup_restore.bat restore "ruta\al\archivo.sql"
if /I "%~1"=="backup" goto :CLI_BACKUP
if /I "%~1"=="restore" (
    set "RESTORE_FILE=%~2"
    goto :CLI_RESTORE
)

:MENU
cls
echo ============================================================================
echo   SISTEMA INTEGRAL E-MARKET EXPRESS - BACKUP Y RESTORE (%DB_NAME%)
echo ============================================================================
echo   Servidor      : %DB_HOST%:%DB_PORT%
echo   Usuario activo: %DB_USER%
echo   Carpeta       : %BACKUP_DIR%
echo ============================================================================
echo.
echo   [1] Backup COMPLETO (esquema + datos + vistas + triggers + SP)
echo   [2] Backup SOLO ESTRUCTURA (DDL + vistas + triggers + SP, sin datos)
echo   [3] Restore desde archivo de respaldo (.sql)
echo   [4] Listar respaldos disponibles
echo   [5] Cambiar usuario de conexion (root / admin_db)
echo   [0] Salir
echo.
set /p "OPC=Selecciona una opcion: "

if "%OPC%"=="1" goto :DO_FULL_BACKUP
if "%OPC%"=="2" goto :DO_SCHEMA_BACKUP
if "%OPC%"=="3" goto :DO_RESTORE
if "%OPC%"=="4" goto :LIST_BACKUPS
if "%OPC%"=="5" goto :SWITCH_USER
if "%OPC%"=="0" exit /b 0
echo.
echo Opcion no valida.
timeout /t 2 >nul
goto :MENU

:GET_TIMESTAMP
for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set "TS=%%T"
if not defined TS set "TS=manual"
exit /b 0

:SET_AUTH_FLAGS
set "AUTH_ARGS=--host=%DB_HOST% --port=%DB_PORT% --user=%DB_USER%"
if defined DB_PASS set "AUTH_ARGS=%AUTH_ARGS% --password=%DB_PASS%"
exit /b 0

:CLI_BACKUP
call :GET_TIMESTAMP
call :SET_AUTH_FLAGS
set "OUT_FILE=%BACKUP_DIR%\backup_%DB_NAME%_%TS%.sql"
"%MYSQLDUMP_BIN%" %AUTH_ARGS% --single-transaction --routines --triggers --events --add-drop-database --databases %DB_NAME% --default-character-set=utf8mb4 --result-file="%OUT_FILE%"
exit /b %errorlevel%

:CLI_RESTORE
if not defined RESTORE_FILE (
    echo [ERROR] Debe indicar la ruta del archivo .sql a restaurar.
    exit /b 1
)
if not exist "%RESTORE_FILE%" (
    echo [ERROR] El archivo no existe: %RESTORE_FILE%
    exit /b 1
)
call :SET_AUTH_FLAGS
"%MYSQL_BIN%" %AUTH_ARGS% --default-character-set=utf8mb4 < "%RESTORE_FILE%"
exit /b %errorlevel%

:DO_FULL_BACKUP
call :GET_TIMESTAMP
call :SET_AUTH_FLAGS
set "OUT_FILE=%BACKUP_DIR%\backup_%DB_NAME%_%TS%.sql"
echo.
echo Generando backup completo en:
echo   %OUT_FILE%
echo.
if /I "%DB_USER%"=="root" (
    "%MYSQLDUMP_BIN%" %AUTH_ARGS% --single-transaction --routines --triggers --events --add-drop-database --databases %DB_NAME% --default-character-set=utf8mb4 --result-file="%OUT_FILE%"
) else (
    "%MYSQLDUMP_BIN%" %AUTH_ARGS% --single-transaction --routines --triggers --events --add-drop-table --no-tablespaces %DB_NAME% --default-character-set=utf8mb4 --result-file="%OUT_FILE%"
)
if errorlevel 1 (
    echo [ERROR] Fallo la generacion del backup. Verifique que MySQL este iniciado en XAMPP y las credenciales.
    if exist "%OUT_FILE%" del /f /q "%OUT_FILE%"
) else (
    echo [OK] Backup completo generado correctamente.
)
echo.
pause
goto :MENU

:DO_SCHEMA_BACKUP
call :GET_TIMESTAMP
call :SET_AUTH_FLAGS
set "OUT_FILE=%BACKUP_DIR%\estructura_%DB_NAME%_%TS%.sql"
echo.
echo Generando backup de estructura (DDL) en:
echo   %OUT_FILE%
echo.
if /I "%DB_USER%"=="root" (
    "%MYSQLDUMP_BIN%" %AUTH_ARGS% --no-data --routines --triggers --events --add-drop-database --databases %DB_NAME% --default-character-set=utf8mb4 --result-file="%OUT_FILE%"
) else (
    "%MYSQLDUMP_BIN%" %AUTH_ARGS% --no-data --routines --triggers --events --add-drop-table --no-tablespaces %DB_NAME% --default-character-set=utf8mb4 --result-file="%OUT_FILE%"
)
if errorlevel 1 (
    echo [ERROR] Fallo la exportacion de estructura.
    if exist "%OUT_FILE%" del /f /q "%OUT_FILE%"
) else (
    echo [OK] Backup de estructura generado correctamente.
)
echo.
pause
goto :MENU

:DO_RESTORE
echo.
echo Respaldos disponibles en %BACKUP_DIR%:
echo ----------------------------------------------------------------------------
set "COUNT=0"
for /f "delims=" %%F in ('dir /b /o-d "%BACKUP_DIR%\*.sql" 2^>nul') do (
    set /a COUNT+=1
    set "FILE_!COUNT!=%%F"
    echo   [!COUNT!] %%F
)
echo   [S] Restaurar desde script base\script.sql (instalacion limpia)
echo   [0] Cancelar
echo.
if "%COUNT%"=="0" echo   (Aun no hay archivos .sql en %BACKUP_DIR%) & echo.

set /p "SEL=Elige el numero del respaldo o S para script.sql: "
if "%SEL%"=="0" goto :MENU

if /I "%SEL%"=="S" (
    set "RESTORE_FILE=%SCRIPT_DIR%\script.sql"
) else (
    call set "CHOSEN=%%FILE_%SEL%%%"
    if not defined CHOSEN (
        echo [ERROR] Seleccion invalida.
        pause
        goto :MENU
    )
    set "RESTORE_FILE=%BACKUP_DIR%\!CHOSEN!"
)

echo.
echo Se restaurara la base de datos '%DB_NAME%' desde:
echo   !RESTORE_FILE!
set /p "CONF=Esta accion sobrescribira los datos actuales. Continuar? (S/N): "
if /I not "%CONF%"=="S" goto :MENU

call :SET_AUTH_FLAGS
echo.
echo Ejecutando restauracion...
"%MYSQL_BIN%" %AUTH_ARGS% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
if errorlevel 1 (
    echo [ERROR] No se pudo verificar/crear la base de datos '%DB_NAME%'.
    pause
    goto :MENU
)

if /I "%SEL%"=="S" (
    "%MYSQL_BIN%" %AUTH_ARGS% --default-character-set=utf8mb4 < "!RESTORE_FILE!"
) else (
    findstr /B /I /C:"USE " "!RESTORE_FILE!" >nul
    if errorlevel 1 (
        "%MYSQL_BIN%" %AUTH_ARGS% --default-character-set=utf8mb4 %DB_NAME% < "!RESTORE_FILE!"
    ) else (
        "%MYSQL_BIN%" %AUTH_ARGS% --default-character-set=utf8mb4 < "!RESTORE_FILE!"
    )
)

if errorlevel 1 (
    echo [ERROR] Ocurrio un error durante la restauracion.
) else (
    echo [OK] Base de datos '%DB_NAME%' restaurada exitosamente.
)
echo.
pause
goto :MENU

:LIST_BACKUPS
echo.
echo Archivos en %BACKUP_DIR%:
echo ----------------------------------------------------------------------------
dir /o-d "%BACKUP_DIR%\*.sql" 2>nul
if errorlevel 1 echo   No hay archivos .sql en la carpeta backups.
echo.
pause
goto :MENU

:SWITCH_USER
echo.
echo   [1] root (sin contrasena - recomendado para backup/restore completo en XAMPP)
echo   [2] admin_db (usuario administrador del esquema parcial)
set /p "UOPT=Elige usuario: "
if "%UOPT%"=="1" (
    set "DB_USER=root"
    set "DB_PASS="
) else if "%UOPT%"=="2" (
    set "DB_USER=admin_db"
    set /p "DB_PASS=Contrasena para admin_db (por defecto Admin2026*Seguro): "
    if not defined DB_PASS set "DB_PASS=Admin2026*Seguro"
)
goto :MENU

