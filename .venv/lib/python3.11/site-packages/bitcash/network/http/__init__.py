from requests import Session

# Create a re-usable session object which re-uses connection, mantains a pool.
session = Session()
# Optional: Configure user-agent here so that upstream servers know which library/version is making the request
