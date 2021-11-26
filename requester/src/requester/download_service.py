import dataclasses
import os
import pathlib
import typing

from loguru import logger

import requester.download as dwn

DEFAULT_TARGET_DIR = pathlib.Path("data") / "games" / "raw"


@dataclasses.dataclass(frozen=True)
class Parameters:
    starting_game_id: dwn.GameID
    overwrite_found_files: bool
    target_directory: pathlib.Path


def parse_env() -> Parameters:
    FALSY_VALUES = ("", "false", "no", "0")

    starting_game_id_str = os.getenv("STARTING_GAME_ID")
    if starting_game_id_str is None:
        raise ValueError("Missing required env var STARTING_GAME_ID")
    # let the normal ValueError raise, no need to catch
    starting_game_id = dwn.GameID(int(starting_game_id_str))

    overwrite_found_files_str = os.getenv("OVERWRITE_OLD_DATA", "false")
    overwrite_found_files = overwrite_found_files_str.lower() not in FALSY_VALUES

    target_dir = pathlib.Path(os.getenv("TARGET_DIRECTORY", DEFAULT_TARGET_DIR))

    return Parameters(starting_game_id, overwrite_found_files, target_dir)


def get_filename(
    target_dir: pathlib.Path, game_id: dwn.GameID
) -> typing.Tuple[str, pathlib.Path]:
    filename = f"{game_id}.json"
    destination = target_dir / filename
    return (filename, destination)


def game_filter(params: Parameters) -> typing.Callable[[dwn.GameID], bool]:
    if params.overwrite_found_files:
        return lambda _: True

    def should_download(game_id: dwn.GameID) -> bool:
        _, path = get_filename(params.target_directory, game_id)
        return not path.exists()

    return should_download


def main() -> None:
    """
    Runs the downloading script and writes the files on disk.
    """
    params = parse_env()

    logger.debug(f"Parsed opts: {params}")

    if not params.target_directory.exists():
        logger.info("Creating download folder structure")
        params.target_directory.mkdir(parents=True)
    else:
        logger.info("Recognized download folder structure")

    game_seq = dwn.download_patch(
        params.starting_game_id,
        on_error_policy=dwn.skip_on_error_policy,
        is_id_valid=game_filter(params),
    )

    for game in game_seq:
        filename, destination = get_filename(params.target_directory, game.game_id)

        with open(destination, "wb") as game_file:
            game_file.write(game.raw)
        logger.info(f"Written bytes=<{len(game.raw)}> to filename=<{filename}>")


if __name__ == "__main__":
    main()
