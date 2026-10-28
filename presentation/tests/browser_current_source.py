"""Use the slide-wide physical policy and pointer-capture regression for current sources."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('browser_physics_audit.py')),run_name='__main__')
