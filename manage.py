#!/usr/bin/env python
import os
import sys


def main():
    """
    Bootstrap the process for running Django management commands by loading environment variables, ensuring the DJANGO_SETTINGS_MODULE default, and dispatching the current process command line to Django's management command runner.
    
    This prepares runtime configuration (including loading a .env file) and then hands control to Django's management command dispatcher to execute the requested management command.
    """
    from dotenv import load_dotenv

    load_dotenv()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()