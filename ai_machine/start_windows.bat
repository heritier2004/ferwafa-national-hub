    echo [INFO] Creating Virtual Environment...
    python -m venv .venv
    echo [INFO] Installing dependencies (this may take a few minutes)...
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
)

:: 3. Run Setup Wizard (checks for config)
echo [INFO] Starting AI Pitch Machine...
.venv\Scripts\python setup_wizard.py

:: 4. Start Main Application
.venv\Scripts\python main.py
pause
