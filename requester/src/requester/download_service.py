import os
import pathlib
import typing

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

    overwrite_found_files_str = os.getenv("OVERWRITE_OLD_DATA", "false")
    overwrite_found_files = overwrite_found_files_str.lower() not in (
        "",
        "false",
        "no",
        "0",
    )

    logger.debug(
        f"Parsed opts: starting_game_id=<{starting_game_id_val}>"
        f", overwrite_old_data=<{overwrite_found_files}>"
    )

    base_dir = pathlib.Path("data") / "games" / "raw"
    if not base_dir.exists():
        logger.info("Creating download folder structure")
        base_dir.mkdir(parents=True)
    else:
        logger.info("Recognized download folder structure")

    def get_filename(game_id: dwn.GameID) -> typing.Tuple[str, pathlib.Path]:
        filename = f"{game_id}.json"
        destination = base_dir / filename
        return (filename, destination)

    def should_download(game_id: dwn.GameID) -> bool:
        _, path = get_filename(game_id)
        return not path.exists()

    def always_download(game_id: dwn.GameID) -> bool:
        return True

    is_id_valid = always_download if overwrite_found_files else should_download

    game_seq = dwn.download_patch(
        starting_game_id_val,
        on_error_policy=dwn.skip_on_error_policy,
        is_id_valid=is_id_valid,
    )

    for game in game_seq:
        filename, destination = get_filename(game.game_id)

        with open(destination, "wb") as game_file:
            game_file.write(game.raw)
        logger.info(f"Written bytes=<{len(game.raw)}> to filename=<{filename}>")


if __name__ == "__main__":
    main()
