@echo off
setlocal
cd /d "%~dp0"
python lcc_converter.py --side both --alpha 145 --mu 15 --output-dir output_lcc
if errorlevel 1 (
  echo Generation failed. Check Python and parameter values.
  exit /b 1
)
echo Figures saved to output_lcc\rectifier and output_lcc\inverter.
endlocal
