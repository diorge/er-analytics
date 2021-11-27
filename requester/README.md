# requester package

The requester package is responsible for downloading
data from the API, and storing its raw form.

This package has to deal with rate limiting,
game ID generation, and overall provide
robustness to the data found (no duplicates, no missing, and so on).

## Downloading

It's recommended to use the Docker containers to execute the download process.
Running `make build` will create a Docker container called `er-requester`.
Attach a volume to this container pointing at `/requester/data`,
and set the envvar `STARTING_GAME_ID`.

For example, after running `make build`, it's possible to do something similar to:

```sh
docker run -it \
    -v /absolute/host/path/:/requester/data \
    -e STARTING_GAME_ID=123456 \
    er-requester \
    python -m requester.download_service
```

Unfortunately Docker will only accept an absolute path for the host machine; you may point it to the path of this repository`/data/`.

## Environment

Use a virtual environment for Python 3.10 (`pyenv` recommended) and `pip install -r requirements/dev.txt`.

Alternatively, a complete Docker environment is provided.
Running `make` or `make build` will create two images, `er-requester` and `er-test`.
Running `make test` will run the test suite.