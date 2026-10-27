@echo off
setlocal
cd /d "%~dp0"
python hvdc_link.py --config config_hvdc.json --all --output-dir output_hvdc
if errorlevel 1 (
  echo Failed. Install Python 3.10 or newer, then retry.
  pause
  exit /b 1
)
echo Completed: output_hvdc\
pause
