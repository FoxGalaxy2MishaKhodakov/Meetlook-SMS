color 2
pip install -r "%~dp0requirements.txt"
pyinstaller --noconfirm --onedir --windowed --icon "%~dp0client\logotip.ico"  "%~dp0client\client.py"