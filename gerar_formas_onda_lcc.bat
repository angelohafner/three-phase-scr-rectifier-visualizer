@echo off
REM Generate all synchronized LCC teaching waveforms and combined vector sheets.
cd /d "%~dp0"
python -m pip install -r requirements-waveforms.txt
if errorlevel 1 exit /b 1
python generate_lcc_waveforms.py --config config_waveforms.json --side all
if errorlevel 1 exit /b 1
python -m pytest -q tests
pause
