@echo off
title Voice Suite 306 - AI Studio
echo ====================================================
echo Starting Voice Suite 306 on Windows 11 (RTX 3060)...
echo ====================================================

:: Check if virtual environment exists
if not exist "venv" (
    echo Creating Windows Python virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing dependencies for CUDA hardware acceleration...
    pip install --upgrade pip
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: Auto-check / download Hugging Face models if missing
python model_downloader.py

:: Launch Master Studio
python studio_app.py
pause
