## Setting Up Development Server (Vagrant)

1. Get [Vagrant](https://www.vagrantup.com/)

2. Get [Virtualbox](https://www.virtualbox.org/)

3. Navigate to the directory with source code and type `vagrant up`. (It takes time during the first run, so go get a coffee!).

4. Now, type `vagrant ssh`.

5. Run `python BLT/manage.py migrate`.

6. Run `python BLT/manage.py createsuperuser`.

7. Run `python BLT/manage.py collectstatic`.

8. Start the server using `python BLT/manage.py runserver`

9. Then go to http://127.0.0.1:8000/admin/socialaccount/socialapp/) and add filler information for social auth accounts. Add a Domain (http://127.0.0.1:8000/admin/website/domain/) with the name 'owasp.org'.

10. visit `http://localhost:8000`.

**Note:** In case you encounter an error with vagrant's vbguest module, run `vagrant plugin install vagrant-vbguest` from the host machine.

## Setting Up Development Server (Virtual Environment)

1. If PostgreSQL is not installed, run:

   - `brew install postgresql` (Mac).

   - `sudo apt-get install postgresql` (Ubuntu).

2. Type `cd BLT`.

3. If virtualenv is not installed, run `sudo apt-get install pipenv` followed by:

   - `pipenv install | pipenv shell` (Ubuntu / Mac).

4. Run `python3 manage.py migrate`.

5. Run `python3 manage.py loaddata website\fixtures\initial_data.json`

6. Run `python3 manage.py createsuperuser`.

7. Run `python3 manage.py collectstatic`.

8. Start the server using `python BLT/manage.py runserver`

9. Then go to http://127.0.0.1:8000/admin/socialaccount/socialapp/) and add filler information for social auth accounts. Add a Domain (http://127.0.0.1:8000/admin/website/domain/) with the name 'owasp.org'.

10. visit `http://localhost:8000`.

**Note:** In case you encounter an error, run `sudo apt-get install libpq-dev`.
