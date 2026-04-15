@echo off
schtasks /create /tn "YouTube AI Analysis Daily Report" /tr "\"%LOCALAPPDATA%\Programs\Python\Python313\python.exe\" \"C:\Users\Arhum\Desktop\Youtube Analysis\tools\run_pipeline.py\"" /sc daily /st 07:00 /f
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Schedule created successfully!
    echo The report will run daily at 7:00 AM.
    echo.
    echo To verify: schtasks /query /tn "YouTube AI Analysis Daily Report"
    echo To delete:  schtasks /delete /tn "YouTube AI Analysis Daily Report" /f
) else (
    echo.
    echo Failed to create schedule. Try running this script as Administrator.
)
pause
