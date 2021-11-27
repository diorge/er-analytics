import os
import pathlib

from loguru import logger

import requester.download as dwn


def main() -> None:
    """
    Runs the downloading script and writes the files on disk.
    """
    starting_game_id = os.getenv("STARTING_GAME_ID")
    if starting_game_id is None:
        raise ValueError("Missing env var STARTING_GAME_ID")

    base_dir = pathlib.Path("data") / "games" / "raw"
    if not base_dir.exists():
        base_dir.mkdir(parents=True)

    for game in dwn.download_patch(dwn.GameID(int(starting_game_id))):
        destination = base_dir / f"{game.game_id}.json"
        with open(destination, "wb") as game_file:
            game_file.write(game.raw)


if __name__ == "__main__":
    main()
