# requester package

The requester package is responsible for downloading
data from the API, and storing it's raw form.

This package has to deal with rate limiting,
game ID generation, and overall provide
robustness to the data found (no duplicates, no missing, and so on).

## Environment

Use a virtual environment for Python 3.10 (`pyenv` recommended) and `pip install -r requirements/dev.txt`.
Docker container alternative coming soon.