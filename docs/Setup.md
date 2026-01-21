# Setting Up Development Server

- [Video on How to setup Project BLT](https://www.youtube.com/watch?v=IYBRVRfPCK8)

## Windows Setup Notes

If you're setting up on **Windows**, please read this section first. The repository includes a `.gitattributes` file that automatically enforces LF line endings for shell scripts and configuration files, preventing CRLF-related issues.

### Quick Windows Setup Checklist

1. **Install Prerequisites:**

   - [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
   - [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) (Windows Subsystem for Linux 2) - **highly recommended** for better compatibility
   - [Git for Windows](https://git-scm.com/download/win) (includes Git Bash) - optional but helpful

2. **Configure Docker Desktop:**

   - Enable WSL2 backend: Docker Desktop → Settings → General → Use WSL 2 based engine
   - Share your drive: Docker Desktop → Settings → Resources → File Sharing (add the drive where your project is located)

3. **Configure Git (recommended):**

   ```bash
   git config --global core.autocrlf input
   ```

   This works together with the `.gitattributes` file to ensure proper line endings.

4. **Line Endings:**

   - The repository's `.gitattributes` file automatically enforces LF line endings for shell scripts (`.sh` files), `.env` files, `docker-compose.yml`, and `Dockerfile`.
   - **For new clones:** Line endings are handled automatically by `.gitattributes` - no action needed.
   - **For existing clones:** If you cloned before `.gitattributes` was added, you will need to manually convert line endings once (see [Line Endings section](#1-ensure-lf-line-endings) below).
   - **Docker fallback:** The Dockerfile includes `dos2unix` commands that convert line endings during the build process, providing an additional safeguard.

5. **PostgreSQL (if not using Docker):**
   - Download from [PostgreSQL official website](https://www.postgresql.org/download/windows/)
   - Or use Chocolatey: `choco install postgresql`
   - Note: Default port is 5432. If you have conflicts, change the port in your `.env` file.

### Windows-Specific Commands

Throughout this guide, you'll see commands for different platforms. For Windows:

- **PowerShell:** Use `Copy-Item` instead of `cp`
- **CMD:** Use `copy` instead of `cp`
- **Git Bash/WSL2:** Can use Unix-style commands like `cp`, `chmod`, etc.

---

## Step 1: Add environment variables

Before proceeding with any setup, you need to configure environment variables.

### 1.Adding environment variables to .env:

- We provide a .env.example file that demonstrates how the environment is set up.

**For Linux/macOS:**

```sh
# --- Move to project directory ---
cd BLT

cp .env.example .env
```

**For Windows:**

```powershell
# --- Move to project directory ---
cd BLT

# Using PowerShell
Copy-Item .env.example .env

# Or using CMD
copy .env.example .env

# Or using Git Bash (if installed)
cp .env.example .env
```

- Modify the .env file as per your local setup.

## Step 2: Choose your setup method (Docker recommended)

#### Prerequisites for Docker method

Ensure the following are installed on your system before proceeding:

- Docker
- Docker Compose
- PostgreSQL client (optional, for manual database interaction)

**Windows-specific prerequisites:**

- Docker Desktop for Windows (includes Docker Compose)
- WSL2 (Windows Subsystem for Linux 2) - **highly recommended** for better compatibility
- Git for Windows (includes Git Bash) - optional but helpful

**Docker Desktop for Windows Configuration:**

- **WSL2 Backend:** Ensure Docker Desktop is using WSL2 backend (Settings → General → Use WSL 2 based engine). This is required for optimal performance and compatibility.
- **Volume Mounting:** Share your drive with Docker Desktop (Settings → Resources → File Sharing). Add the drive where your project is located.
- **Resource Allocation:** Adjust CPU and memory allocation in Settings → Resources if needed (minimum 4GB RAM recommended).

---

### 1. Ensure LF Line Endings

Before building the Docker images, ensure all files, especially scripts like `entrypoint.sh`, `.env`, `docker-compose.yml`, `Dockerfile`, `settings.py` use LF line endings. Using CRLF can cause build failures.

**Good News:** The repository includes a `.gitattributes` file that automatically enforces LF line endings for shell scripts and configuration files. Additionally, the Dockerfile includes `dos2unix` commands that convert line endings during the build process as a fallback.

- **For new clones:** Line endings are handled automatically by `.gitattributes` - no manual conversion needed.
- **For existing clones:** If you cloned before `.gitattributes` was added, you will need to manually convert line endings once (see options below).
- **Docker build safety:** Even if line endings are incorrect, the Dockerfile will convert them during the build process, so `docker-compose build` will succeed.

**To verify and correct line endings (if needed):**

1. **Recommended: Configure Git to work with `.gitattributes`:**

   - Set `core.autocrlf=input` in Git configurations to enforce LF-style line endings in the repository while preserving your local OS line endings.
     ```bash
     git config --global core.autocrlf input
     ```
   - This works together with `.gitattributes` to ensure proper line endings on checkout.

2. **Alternative: Manual conversion in VS Code:**

   - Open the file in the editor.
   - Look for the line ending type displayed in the bottom-right corner of the VS Code window (e.g., CRLF or LF).
   - Click it and select "LF: Unix" from the dropdown to switch the line endings to LF.
   - Save the file.

3. If the browser **automatically redirects to HTTPS** even in incognito mode, you can try the following:  
   For **local development**, make these adjustments in `/blt/settings.py` to enable access over **HTTP**:

   - Set:
     ```python
     SECURE_SSL_REDIRECT = False
     SECURE_PROXY_SSL_HEADER = None
     ```

4. **Manual conversion to LF (only needed for existing clones or if `.gitattributes` didn't work):**

   **For Linux/macOS:**

   - Using `dos2unix`:
     ```bash
     dos2unix scripts/entrypoint.sh
     ```

   **For Windows:**

   - **Option 1: Using Git Bash** (if Git for Windows is installed):

     ```bash
     dos2unix scripts/entrypoint.sh
     ```

     Note: If `dos2unix` is not available, install it via: `pacman -S dos2unix` (in Git Bash)

   - **Option 2: Using PowerShell**:

     ```powershell
     # Convert CRLF to LF using PowerShell
     (Get-Content scripts/entrypoint.sh -Raw) -replace "`r`n", "`n" | Set-Content scripts/entrypoint.sh -NoNewline
     ```

   - **Option 3: Using VS Code** (recommended for Windows):

     - Open the file in VS Code
     - Click on the line ending indicator in the bottom-right (CRLF/LF)
     - Select "LF" from the dropdown
     - Save the file

   - **Option 4: Using WSL2** (if WSL2 is installed):
     ```bash
     # In WSL2 terminal
     dos2unix scripts/entrypoint.sh
     ```

⚠️ **Important:**

- The `.gitattributes` file prevents line ending issues for new clones.
- The Dockerfile includes `dos2unix` commands that automatically convert line endings during build, so `docker-compose build` will succeed even with incorrect line endings.
- If you're working with an existing clone (before `.gitattributes` was added), you can either:
  - Manually convert line endings once (see options above), or
  - Rely on the Dockerfile's automatic conversion during build
- Avoid creating a PR to commit local line ending changes back to the repository.

### 2. PostgreSQL Setup

The PostgreSQL database listens on a port specified in the `.env` file.
The default port is 5432. If you encounter port conflicts, change the port in your `.env` file (e.g., 5433).

**Note:** If you're using Docker (recommended method), PostgreSQL runs inside a container and you don't need to install it separately. The following instructions are only needed if you're setting up without Docker.

**Installing PostgreSQL (if not using Docker):**

- **Linux (Ubuntu/Debian):**

  ```bash
  sudo apt-get install postgresql
  ```

- **macOS:**

  ```bash
  brew install postgresql
  ```

- **Windows:**
  1. Download PostgreSQL from the [official website](https://www.postgresql.org/download/windows/)
  2. Run the installer and follow the setup wizard
  3. Remember the password you set for the `postgres` user
  4. PostgreSQL will run as a Windows service by default
  5. You can also use [Chocolatey](https://chocolatey.org/) (if installed):
     ```powershell
     choco install postgresql
     ```

---

## Commands to Set Up the Project

- **Copy and configure the `.env` file:**  
   **Linux/macOS/Git Bash:**

  ```bash
  cp .env.example .env
  ```

  **Windows (PowerShell):**

  ```powershell
  Copy-Item .env.example .env
  ```

  **Windows (CMD):**

  ```cmd
  copy .env.example .env
  ```

  Update credentials and settings as needed.

- #### Build the Docker images:
  ```bash
  docker-compose build
  ```
- #### Start the containers:
  ```bash
  docker-compose up
  ```
- #### Access the application:

- Open your browser and navigate to:
  http://localhost:8000/
- #### Prevent Automatic Redirects to HTTPS:
- Use Incognito Mode (Private Browsing): Open the browser in incognito mode and access the application using http://localhost:8000.
- Ensure you're explicitly using http:// instead of https:// in the URL.

### Notes

- The project listens on port 8000 over the HTTP protocol.
- Ensure all required configurations in .env are correct for seamless setup.

### Error Edge Cases

**Permission errors:**

- **Linux/macOS/Git Bash/WSL2:** If container fails to execute `./scripts/entrypoint.sh` due to permission error, use:
  ```bash
  chmod +x scripts/entrypoint.sh
  ```
- **Windows (PowerShell/CMD):** The `chmod` command is not available in native Windows terminals. This is not needed when using Docker, as:
  - File permissions are handled by the container
  - The Dockerfile explicitly sets script permissions with `chmod +x /blt/scripts/entrypoint.sh` (line 67)
  - If you encounter permission issues, ensure Docker Desktop is using WSL2 backend

**Script not found errors:**

- If you encounter `./scripts/entrypoint.sh was not found`, then make sure you are using `LF` line ending in place of `CRLF`. See the [line endings section](#1-ensure-lf-line-endings) above for Windows-specific solutions.

**SSL/HTTPS redirect errors:**

- If you encounter `ERR_SSL_PROTOCOL_ERROR` when you try to access the server on http://localhost:8000, make sure the Browser doesn't automatically redirect to https://localhost:8000. If it keeps doing this behaviour, then you can set `SECURE_SSL_REDIRECT` to `False` locally only (search for it in `/blt/settings.py`), stop the container and start it again.
- If you encounter the same error indicating SSL_REDIRECT in the logs while building the container, set `SECURE_SSL_REDIRECT` to `False`

**Windows-specific Docker issues:**

- **Volume permissions:** If you encounter permission issues with Docker volumes on Windows:
  - Ensure Docker Desktop is using WSL2 backend (Settings → General → Use WSL 2 based engine)
  - Share your drive with Docker Desktop (Settings → Resources → File Sharing)
- **Port conflicts:** If port 8000 or 5432 is already in use:
  - Check what's using the port: `netstat -ano | findstr :8000` (Windows) or `lsof -i :8000` (Linux/macOS)
  - Change the port in your `.env` file if needed

### Option 2.Setting up development server using vagrant

-Install [vagrant](https://www.vagrantup.com/)

-Get [virtualbox](https://www.virtualbox.org/)

#### Follow the given commands

```sh

 # Start vagrant - It takes time during the first run, so go get a coffee!
 vagrant up

 # SSH into vagrant
 vagrant ssh

 # Move to project directory
 cd BLT

 # Create tables in the database
 python manage.py migrate

 # Create a super user
 python manage.py createsuperuser

 # Collect static files
 python manage.py collectstatic

 # Run the server
 python manage.py runserver
```

#### Ready to go

Then go to `http://127.0.0.1:8000/admin/socialaccount/socialapp/` and add filler information for social auth accounts.
Add a Domain `http://127.0.0.1:8000/admin/website/domain/` with the name 'owasp.org'.

#### Voila go visit `http://localhost:8000`

**Note:** In case you encounter an error with vagrant's vbguest module, run `vagrant plugin install vagrant-vbguest`
from the host machine.

### Option 3.Setting up development server using python virtual environment

#### Setup correct python version

Current supported python version is `3.11.2`. It can be installed using any tool of choice like `asdf`, `pyenv`, `hatch`.
For this guide, we are using `pyenv`. Install pyenv by following instructions in its [Github Repo](https://github.com/pyenv/pyenv?tab=readme-ov-file#installation)

```sh
pyenv install 3.11.2

```

Note: Project root folder already contains `.python-version`, so pyenv can recognize the local version to use for the current project.

#### Setup virtual environment using poetry

Ensure that `python -V` returns the correct python version for the project

```sh
# --- Install postgres ---

# Install postgres on macOS
brew install postgresql

# Install postgres on Ubuntu/Debian
sudo apt-get install postgresql

# Install postgres on Windows
# Download from: https://www.postgresql.org/download/windows/
# Or use Chocolatey: choco install postgresql

# --- Setup Virtual Environment ---
# Install Poetry
pip install poetry

# Activate virtual environment
poetry shell

# Install required dependencies
poetry install

# --- Project setup ---
# Create tables in the database
python manage.py migrate

# Load initial data
python3 manage.py loaddata website/fixtures/initial_data.json

# Create a super user
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run the server
python manage.py runserver
```

#### Ready to go now

Then go to `http://127.0.0.1:8000/admin/socialaccount/socialapp/` and add filler information for social auth accounts.
Add a Domain `http://127.0.0.1:8000/admin/website/domain/` with the name 'owasp.org'.

#### Visit `http://localhost:8000`

**Note:** In case you encounter an error related to PostgreSQL development libraries:

- **Linux (Ubuntu/Debian):** Run `sudo apt-get install libpq-dev`
- **macOS:** Usually included with PostgreSQL installation via Homebrew
- **Windows:** The PostgreSQL Windows installer typically includes all necessary libraries. If you encounter issues, ensure PostgreSQL is properly installed and the `PATH` environment variable includes the PostgreSQL `bin` directory

## Troubleshooting

If you run into issues during the setup, here are some common solutions:

### 1.Cannot install nltk, distlib, certifi

The error message indicates that the package manager (Poetry) is unable to find installation candidates.
Below are the temporary solutions.

```sh
poetry cache clear --all pypi

#For Docker method only
docker-compose build --no-cache
```

Feel free to contribute by solving this [issue](https://github.com/OWASP-BLT/BLT/issues/2659).

## Need more help?

If you're still facing issues or need further assistance, feel free to reach out to the community on the [OWASP Slack channel](https://owasp.org/slack/invite).
## Email Verification in Local Development
This section explains how to bypass email verification locally when no email backend is configured.

When running BLT locally, you may encounter a **“Verify Your Email Address”**
screen after creating a user or superuser.

This happens because BLT uses `django-allauth`, which enforces email verification
by default, but no email backend is configured for local development.

### Local Development Workaround

If you are running BLT locally (for example, using Docker) and want to log in
immediately, you can manually mark your email as verified using the Django shell.

Run:

```bash
docker-compose exec app python manage.py shell

