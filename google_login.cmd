@echo off
pushd "%~dp0backend"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m cli google-login
) else (
  python -m cli google-login
)
popd
