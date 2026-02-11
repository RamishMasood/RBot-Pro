@echo off
REM Creates a Windows scheduled task that runs fast_analysis.py every 5 minutes
SET PYTHON=%~dp0\..\..\Python\python.exe
REM Use system python if installed in PATH
schtasks /Create /SC MINUTE /MO 5 /TN "FastAnalysis" /TR "python "%~dp0fast_analysis.py"" /F
echo Scheduled task 'FastAnalysis' created to run every 5 minutes.
pause
