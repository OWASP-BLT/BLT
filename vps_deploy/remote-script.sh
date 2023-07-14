#!/bin/bash

sudo apt-get update -y
sudo apt-get upgrade -y

sudo apt-get install -y python3-pip python3-dev libpq-dev postgresql postgresql-contrib nginx curl git

pip3 install --user virtualenv

declare -A arr
arr["project1.com"]="https://github.com/user/project1.git"
arr["project2.com"]="https://github.com/user/project2.git"


for project in "${!arr[@]}"
do
  mkdir ~/$project
  
  cd ~/$project
  
  python3 -m venv $project-env
  source $project-env/bin/activate
  
  git clone ${arr[$project]}
  
  pip install django gunicorn psycopg2-binary
  
  python manage.py collectstatic
  
  sudo -u postgres createuser $project
  sudo -u postgres createdb $project
  
  sudo -u postgres psql -c "ALTER USER $project PASSWORD 'yourpassword';"
  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $project TO $project;"
    
  sudo ln -s ~/$project/gunicorn.service /etc/systemd/system/
  
  sudo ln -s ~/$project/$project /etc/nginx/sites-enabled
  
  sudo systemctl daemon-reload
  sudo systemctl restart gunicorn
  sudo systemctl restart nginx
done
