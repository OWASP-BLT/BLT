# Vagrant Development Environment Setup

This document provides detailed instructions for setting up and managing the Vagrant environment for the project.

## Prerequisites

1. Install [Vagrant](https://www.vagrantup.com/)
2. Install [VirtualBox](https://www.virtualbox.org/)

## Setting Up the Vagrant Environment

1. Navigate to the project directory:
   ```sh
   cd BLT
   ```

2. Start Vagrant (It takes time during the first run, so go get a coffee!):
   ```sh
   vagrant up
   ```

3. SSH into Vagrant:
   ```sh
   vagrant ssh
   ```

4. Move to the project directory:
   ```sh
   cd BLT
   ```

5. Create tables in the database:
   ```sh
   python manage.py migrate
   ```

6. Create a super user:
   ```sh
   python manage.py createsuperuser
   ```

7. Collect static files:
   ```sh
   python manage.py collectstatic
   ```

8. Run the server:
   ```sh
   python manage.py runserver
   ```

## Managing the Vagrant Environment

1. To halt the Vagrant environment:
   ```sh
   vagrant halt
   ```

2. To reload the Vagrant environment:
   ```sh
   vagrant reload
   ```

3. To destroy the Vagrant environment:
   ```sh
   vagrant destroy
   ```

## Common Vagrant Commands

1. List all Vagrant environments:
   ```sh
   vagrant global-status
   ```

2. Suspend the Vagrant environment:
   ```sh
   vagrant suspend
   ```

3. Resume the Vagrant environment:
   ```sh
   vagrant resume
   ```

## Troubleshooting Tips

1. If you encounter issues with Vagrant, ensure that VirtualBox is installed and running.
2. Check the Vagrant logs for any error messages:
   ```sh
   vagrant up --debug
   ```
