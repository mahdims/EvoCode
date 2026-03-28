@echo off
REM ============================================================================
REM Build AILSII.jar from Source (Windows Batch)
REM ============================================================================
REM Compiles all Java source files and packages them into a JAR file
REM
REM Usage:
REM   build_jar.bat
REM ============================================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set SRC_DIR=%PROJECT_DIR%\src
set BUILD_DIR=%PROJECT_DIR%\build
set JAR_FILE=%PROJECT_DIR%\AILSII.jar

echo ============================================================================
echo Building AILSII.jar
echo ============================================================================
echo Project directory: %PROJECT_DIR%
echo Source directory: %SRC_DIR%
echo.

REM Check if source directory exists
if not exist "%SRC_DIR%" (
    echo Error: Source directory not found: %SRC_DIR%
    exit /b 1
)

REM Create build directory
echo Step 1: Creating build directory...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"

REM Find all Java files
echo.
echo Step 2: Finding Java source files...
set JAVA_FILES=
for /r "%SRC_DIR%" %%f in (*.java) do (
    set JAVA_FILES=!JAVA_FILES! "%%f"
)

REM Compile all Java files
echo.
echo Step 3: Compiling Java sources...
javac -d "%BUILD_DIR%" -sourcepath "%SRC_DIR%" %JAVA_FILES%

if errorlevel 1 (
    echo.
    echo Error: Compilation failed
    exit /b 1
)

echo Compilation successful!

REM Create manifest file
echo.
echo Step 4: Creating JAR manifest...
(
    echo Manifest-Version: 1.0
    echo Main-Class: SearchMethod.AILSII
    echo Created-By: build_jar.bat
) > "%BUILD_DIR%\MANIFEST.MF"

REM Create JAR file
echo.
echo Step 5: Creating JAR file...
pushd "%BUILD_DIR%"
jar cfm "%JAR_FILE%" MANIFEST.MF .
popd

if errorlevel 1 (
    echo.
    echo Error: JAR creation failed
    exit /b 1
)

REM Verify JAR file
echo.
echo Step 6: Verifying JAR file...
if exist "%JAR_FILE%" (
    echo JAR file created successfully: %JAR_FILE%
) else (
    echo Error: JAR file not found after build
    exit /b 1
)

REM Cleanup build directory
echo.
echo Step 7: Cleaning up...
rmdir /s /q "%BUILD_DIR%"
echo Build directory removed

echo.
echo ============================================================================
echo Build Complete!
echo ============================================================================
echo JAR file: %JAR_FILE%
echo.
echo Test the JAR with:
echo   java -jar AILSII.jar -file data/XL/XL-n1048-k237.vrp -rounded true -best 0 -limit 30 -stoppingCriterion Time
echo ============================================================================

endlocal
