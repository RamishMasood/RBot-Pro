@echo off
cd /d %~dp0
REM Run fast_analysis.py and append stdout/stderr to fast_analysis.log
 python -X utf8 fast_analysis.py >> "%~dp0fast_analysis.log" 2>&1
 set PYTHONUTF8=1
 set PYTHONIOENCODING=utf-8
