# Python Virtual Environment Setup Instructions

## Setting Up the Python Version

1. Ensure the correct Python version is installed:
   ```sh
   pyenv install 3.11.2
   ```
2. Set the local Python version:
   ```sh
   pyenv local 3.11.2
   ```

## Setting Up the Virtual Environment

1. Install Poetry:
   ```sh
   pip install poetry
   ```
2. Activate the virtual environment:
   ```sh
   poetry shell
   ```
3. Install required dependencies:
   ```sh
   poetry install
   ```

## Project Setup

1. Create tables in the database:
   ```sh
   python manage.py migrate
   ```
2. Load initial data:
   ```sh
   python3 manage.py loaddata website/fixtures/initial_data.json
   ```
3. Create a super user:
   ```sh
   python manage.py createsuperuser
   ```
4. Collect static files:
   ```sh
   python manage.py collectstatic
   ```
5. Run the server:
   ```sh
   python manage.py runserver
   ```

## Managing the Virtual Environment

1. To deactivate the virtual environment:
   ```sh
   exit
   ```
2. To reactivate the virtual environment:
   ```sh
   poetry shell
   ```

## Common Commands

1. List installed packages:
   ```sh
   poetry show
   ```
2. Add a new dependency:
   ```sh
   poetry add <package_name>
   ```
3. Remove a dependency:
   ```sh
   poetry remove <package_name>
   ```

## Troubleshooting Tips

1. If you encounter issues with the virtual environment, ensure that the correct Python version is being used.
2. Check the Poetry logs for any error messages:
   ```sh
   poetry install -vvv
   ```
