export PATH=$PATH:/usr/local/bin:/usr/bin:/bin:/app/vendor/firefox
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib:/usr/lib:/lib:/app/vendor/firefox
# xvfb :99 -ac
# export DISPLAY=:99
echo ${GOOGLE_CREDENTIALS} > /app/google-credentials.json

