# OWASP BLT

**Report issues and get points, companies are held accountable.**

Live Site: [Bugheist](http://bugheist.com/)

## Dev Setup
**Step 1:**

If PostgreSQL is not installed, run 

`brew install postgresql` (Mac)

`sudo apt-get install postgresql` (Ubuntu) 

**Step 2:**

`cd BLT`

**Step 3:**

If virtualenv is not installed, run `sudo apt-get install virtualenv` followed by

`virtualenv venv` (Ubuntu)

`venv\Scripts\activate` (Windows)

`source venv/bin/activate` (Mac)

**Step 4:**

`pip install -r requirements.txt`

**Step 5:**

`python manage.py migrate`

**Step 6:**

`python manage.py createsuperuser`

then go to http://127.0.0.1:8000/admin/socialaccount/socialapp/) and add filler information for social auth accounts.Add a Domain with the name 'owasp.com' .

**Step 7:**

Start the server using `python manage.py runserver` and visit http://localhost:8000

**Note:** In case you encounter an error, run `sudo apt-get install libpq-dev`

## Resources

- Join the [OWASP Slack Channel](https://owasp.herokuapp.com/) and ask questions at **#project-blt**.

## Notes

- If you find a bug or have an improvement, use BLT to report it!

## Code Sprint 2017 Challenge

-  OWASP Code Sprint 2017
- Add your name / Github link here along with your proposal

