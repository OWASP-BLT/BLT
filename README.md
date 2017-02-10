# OWASP BLT

Report issues and get points, companies are held accountable.

The first time you may need to run:
- `If postgresql is not installed`, `brew install postgresql` (mac), `sudo apt-get install postgresql` (Ubuntu) 

- `cd bugheist`
- `virtualenv venv`
- `venv\Scripts\activate` (windows)
- `source venv/bin/activate` (mac)
- `pip install -r requirements.txt`
- `python manage.py migrate`
- `python manage.py createsuperuser` (then go to /admin) and add filler information for social auth accounts
- `python manage.py runserver`

Note:
- `you may have to install libpq-dev`
