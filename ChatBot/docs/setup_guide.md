# Winfo AI Agents API – Setup & Installation Guide

This guide provides step-by-step instructions to install Python 3.12, set up dependencies, configure your environment, and run the project using Uvicorn on both **Windows** and **Linux**.

---

## 1. Install Python 3.12

### Windows
1. Download the Python 3.12 installer from the [official Python website](https://www.python.org/downloads/release/python-3120/).
2. Run the installer. **Check the box** for "Add Python 3.12 to PATH" before clicking "Install Now".
3. Verify installation:
   ```powershell
   python --version
   # or
   python3 --version
   ```
   Output should be `Python 3.12.x`.

### Linux (Ubuntu/Debian)
1. Update and install prerequisites:
   ```bash
   sudo apt update
   sudo apt install -y wget build-essential libssl-dev zlib1g-dev libbz2-dev \
     libreadline-dev libsqlite3-dev curl libncursesw5-dev xz-utils tk-dev \
     libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
   ```
2. Download and install Python 3.12:
   ```bash
   wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz
   tar -xf Python-3.12.0.tgz
   cd Python-3.12.0
   ./configure --enable-optimizations
   make -j $(nproc)
   sudo make altinstall
   ```
3. Verify installation:
   ```bash
   python3.12 --version
   ```

---

## 2. Set Up a Virtual Environment (Recommended)

### Windows
```powershell
python -m venv venv
venv\Scripts\activate
```

### Linux
```bash
python3.12 -m venv venv
source venv/bin/activate
```

---

## 3. Install Project Dependencies

```sh
pip install --upgrade pip
pip install -r configuration/requirements.txt
```

---

## 4. Prepare Configuration Files

- Place the following files in the `configuration/` directory:
  - `db_config.json`
  - `Google_Key(WAI).json`
  - `jira_config.json`
- Ensure SSL certificates are available at:
  - `../certs/fullchain.pem`
  - `../certs/privkey.pem`
  - `../certs/oci_private.pem`

---

## 5. Create Required Directories

### Windows
```powershell
mkdir DownloadedFiles\AgentFiles
mkdir DownloadedFiles\JiraFiles
mkdir DownloadedFiles\SupportDocs
mkdir logs
```

### Linux
```bash
mkdir -p DownloadedFiles/AgentFiles DownloadedFiles/JiraFiles DownloadedFiles/SupportDocs logs
```

---

## 6. Run the Project Using Uvicorn

You can run the project directly with Python (as in `Process.py`), or use Uvicorn for more control:

### Option 1: Run with Python (default)
```sh
python Process.py
```

### Option 2: Run with Uvicorn (manual)
#### Windows
```powershell
uvicorn Process:app --host 0.0.0.0 --port 8110 --ssl-keyfile ../certs/privkey.pem --ssl-certfile ../certs/fullchain.pem --timeout-keep-alive 0
```
#### Linux
```bash
uvicorn Process:app --host 0.0.0.0 --port 8110 --ssl-keyfile ../certs/privkey.pem --ssl-certfile ../certs/fullchain.pem --timeout-keep-alive 0
```

- The server will start on port `8110` with HTTPS enabled.
- Access the API endpoints via `https://localhost:8110/` (or your server's IP/domain).

---

## 7. Troubleshooting
- If you see `ModuleNotFoundError`, ensure your virtual environment is activated and dependencies are installed.
- For SSL errors, verify the certificate paths and permissions.
- For database connection issues, check your `db_config.json` and network access.

---

## 8. Useful Commands
- **Deactivate virtual environment:**
  - Windows: `deactivate`
  - Linux: `deactivate`
- **Upgrade pip:**
  ```sh
  python -m pip install --upgrade pip
  # or
  python3.12 -m pip install --upgrade pip
  ```

---

## 9. Additional Notes
- All endpoints require HTTPS and are CORS-restricted to `winfosolutions.com` domains.
- For more details, see the API documentation in `docs/README.md`.

---

## License
Proprietary. All rights reserved by Winfo Solutions.
