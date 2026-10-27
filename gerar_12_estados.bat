@echo off
REM Generate all twelve SVG states from the extracted package directory.
cd /d "%~dp0"
python retificador_trifasico_inkscape.py --all-12 --mu 15 --output-dir output
if errorlevel 1 (
    echo.
    echo SVG generation failed. Verify your Python installation.
) else (
    echo.
    echo Generated twelve SVGs and a comparison panel in the output folder.
)
pause
