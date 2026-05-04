@echo off
TITLE MBD CAD Suite Launcher
echo ===================================================
echo Starting Engineering CAD Suite...
echo ===================================================

:: 1. Navigate to the folder where this .bat file is saved
cd /d "%~dp0"

:: 2. Find Conda and activate the environment
echo Booting up the Python CAD environment...
IF EXIST "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\anaconda3\Scripts\activate.bat" occ_env
) ELSE IF EXIST "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\miniconda3\Scripts\activate.bat" occ_env
) ELSE IF EXIST "C:\ProgramData\anaconda3\Scripts\activate.bat" (
    call "C:\ProgramData\anaconda3\Scripts\activate.bat" occ_env
) ELSE IF EXIST "C:\ProgramData\miniconda3\Scripts\activate.bat" (
    call "C:\ProgramData\miniconda3\Scripts\activate.bat" occ_env
) ELSE (
    echo [!] ERROR: Could not locate Anaconda or Miniconda.
    pause
    exit
)

:: 3. Launch the Streamlit application
echo Launching Dashboard...
streamlit run app.py

:: 4. Keep the window open if the app crashes
pause