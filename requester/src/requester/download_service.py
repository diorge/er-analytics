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

    # let the normal ValueError raise, no need to catch
    starting_game_id_val = dwn.GameID(int(starting_game_id))

    base_dir = pathlib.Path("data") / "games" / "raw"
    if not base_dir.exists():
        logger.info("Creating download folder structure")
        base_dir.mkdir(parents=True)
    else:
        logger.info("Recognized download folder structure")

    game_seq = dwn.download_patch(
        starting_game_id_val, on_error_policy=dwn.skip_on_error_policy
    )

    for game in game_seq:
        filename = f"{game.game_id}.json"
        destination = base_dir / filename
        with open(destination, "wb") as game_file:
            game_file.write(game.raw)
        logger.info(f"Written bytes=<{len(game.raw)}> to filename=<{filename}>")


if __name__ == "__main__":
    main()
