# Setting Up Development Server

- [Video on How to setup Project BLT](https://www.youtube.com/watch?v=IYBRVRfPCK8)

## Step 1: Add environment variables
Before proceeding with any setup, you need to configure environment variables.

### 1.Adding environment variables to .env:
- We provide a .env.example file that demonstrates how the environment is set up.

```sh
# --- Move to project directory ---
cd BLT

cp .env.example .env
```
- Modify the .env file as per your local setup.
## Step 2: Choose your setup method (Docker recommended)
#### Prerequisites for Docker method
Ensure the following are installed on your system before proceeding:

- Docker  
- Docker Compose  
- PostgreSQL client (optional, for manual database interaction)  
---
---

## Bounty Payout Automation Environment Variables

To enable secure and automated bounty payouts via GitHub Sponsors, set the following environment variables in your `.env` file:

- `BLT_API_TOKEN`: Secret token for authenticating payout requests from GitHub Actions. Must match the token used in your workflow.
- `GITHUB_SPONSOR_USERNAME`: The GitHub account that will sponsor users (default: `DonnieBLT`).
- `BLT_ALLOWED_BOUNTY_REPO_1`, `BLT_ALLOWED_BOUNTY_REPO_2`, `BLT_ALLOWED_BOUNTY_REPO_3`: List of repositories eligible for bounty payouts. Only issues from these repos will be processed for payouts. This is a critical security measure to prevent unauthorized repositories from draining the bounty budget.

Example:

```env
BLT_API_TOKEN=your-bounty-api-token-here
GITHUB_SPONSOR_USERNAME=DonnieBLT
BLT_ALLOWED_BOUNTY_REPO_1=OWASP-BLT/BLT
BLT_ALLOWED_BOUNTY_REPO_2=other-org/other-repo
BLT_ALLOWED_BOUNTY_REPO_3=another-org/another-repo
```

**Important:**
- Never share your `BLT_API_TOKEN` publicly.
- Always keep the allowed repo list up to date to ensure only trusted repositories are eligible for payouts.
### 1. Ensure LF Line Endings
Before building the Docker images, ensure all files, especially scripts like `entrypoint.sh`, `.env`, `docker-compose.yml`, `Dockerfile`, `settings.py` use LF line endings. Using CRLF can cause build failures. To verify and correct line endings:

1. If you're working on a Windows machine or collaborating across different operating systems, ensure consistent line endings:
   - Set `core.autocrlf=input` in Git configurations to enforce LF-style line endings in the repository while preserving your local OS line endings.
     ```bash
     git config --global core.autocrlf input
     ```
   - Alternatively, in VS Code, you can manually change the line endings:
     - Open the file in the editor.
     - Look for the line ending type displayed in the bottom-right corner of the VS Code window (e.g., CRLF or LF).
     - Click it and select "LF: Unix" from the dropdown to switch the line endings to LF.

2. If the browser **automatically redirects to HTTPS** even in incognito mode, you can try the following:  
   For **local development**, make these adjustments in `/blt/settings.py` to enable access over **HTTP**:
   - Set:
     ```python
     SECURE_SSL_REDIRECT = False
     SECURE_PROXY_SSL_HEADER = None
     ```

3. To convert to LF (if needed):  
   - Using `dos2unix`:
     ```bash
     dos2unix entrypoint.sh
     ```

⚠️ **Important:**  
- If line endings are not set to LF, running `docker-compose build` may fail.  
- Avoid creating a PR to commit these local changes back to the repository.

### 2. PostgreSQL Setup
The PostgreSQL database listens on a port specified in the .env file.
Default is 5432 and
If you encounter conflicts, it might be set to another port (e.g., 5433 in some cases). Adjust the .env file accordingly.

---

## Commands to Set Up the Project

- **Copy and configure the `.env` file:**  
   ```bash
   cp .env.example .env
Update credentials and settings as needed.

- #### Build the Docker images:
  ```bash
  docker-compose build
- #### Start the containers:
  ```bash
  docker-compose up
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
- If container fails execute ./entrypoint.sh due to permission error, use `chmod +x ./entrypoint.sh`
- If you encounter ./entrypoint.sh was not found, then make sure you are using `LF` line ending in place of `CRLF`
- If you encounter ERR_SSL_PROTOCOL_ERROR when you try to access the server on http://localhost:8000, make sure the Browser doesn't automatically redirect to https://localhost:8000. If it keeps doing this behaviour, then you can set `SECURE_SSL_REDIRECT` to `False` locally only(search for it  /blt/settings.py), stop the container and start it again.
- If you encounter the same error indicating SSL_REDIRECT in the logs while building the container, set `SECURE_SSL_REDIRECT` to `False`

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

# Install postgres on mac
brew install postgresql

# Install postgres on ubuntu
sudo apt-get install postgresql

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

**Note:** In case you encounter an error, run `sudo apt-get install libpq-dev`.

## Troubleshooting
If you run into issues during the setup, here are some common solutions:

### 1.Cannot install nltk, distlib, certifi 
The error message you're encountering suggests that the package manager (likely poetry) is unable to find installation candidates.
Below are the temporary solutions.

```sh
poetry cache clear --all pypi

#For Docker method only
docker-compose build --no-cache 
```
Feel free to contribute by solving this [issue](https://github.com/OWASP-BLT/BLT/issues/2659).

## Need more help?
If you're still facing issues or need further assistance, feel free to reach out to the community on the [OWASP Slack channel](https://owasp.org/slack/invite).
