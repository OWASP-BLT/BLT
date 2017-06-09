# OWASP BLT

**Report issues and get points, companies are held accountable.**

Live Site: [Bugheist](http://bugheist.com/)

## Setting Up Development Server (Vagrant)

1. Get [Vagrant](https://www.vagrantup.com/)

2. Get [Virtualbox](https://www.virtualbox.org/)

3. Navigate to the directory with source code and type `vagrant up`. (It takes time during the first run, so go get a coffee!).

4. Now, type `vagrant ssh`.

5. Run `python BLT/manage.py migrate`.

6. Run `python BLT/manage.py createsuperuser`.

7. Start the server using `python BLT/manage.py runserver 0.0.0.0:8000` and visit `http://localhost:8000`.

8. Then go to http://127.0.0.1:8000/admin/socialaccount/socialapp/) and add filler information for social auth accounts. Add a Domain (http://127.0.0.1:8000/admin/website/domain/)   with the name 'owasp.com'.

**Note:** In case you encounter an error with vagrant's vbguest module, run `vagrant plugin install vagrant-vbguest` from the host machine.

## Setting Up Development Server (Virtual Environment)

1. If PostgreSQL is not installed, run:

    * `brew install postgresql` (Mac).

    * `sudo apt-get install postgresql` (Ubuntu).

2. Type `cd BLT`.

3. If virtualenv is not installed, run `sudo apt-get install virtualenv` followed by:

    * `virtualenv venv` (Ubuntu).

    * `venv\Scripts\activate` (Windows).

    * `source venv/bin/activate` (Mac).

4. Run `pip install -r requirements.txt`.

5. Run `python manage.py migrate`.

6. Run `python manage.py createsuperuser`.

7. Then go to http://127.0.0.1:8000/admin/socialaccount/socialapp/) and add filler information for social auth accounts. Add a Domain with the name 'owasp.com'.

8. Start the server using `python manage.py runserver` and visit `http://localhost:8000`.

**Note:** In case you encounter an error, run `sudo apt-get install libpq-dev`.

## Resources

- Join the [OWASP Slack Channel](https://owasp.herokuapp.com/) and ask questions at **#project-blt**.

## Notes

- If you find a bug or have an improvement, use BLT to report it!

## Code Sprint 2017 Challenge

- OWASP Code Sprint 2017.
- Add your name / Github link here along with your proposal.

