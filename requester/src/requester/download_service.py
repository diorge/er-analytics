import dataclasses
import enum
import os
import pathlib
import typing

from loguru import logger

import requester.download as dwn

DEFAULT_TARGET_DIR = pathlib.Path("data") / "games" / "raw"


class RetryProfile(enum.Enum):
    STANDARD = enum.auto()
    AGGRESSIVE = enum.auto()

    def retry_timers(self) -> tuple[float, ...]:
        return {
            RetryProfile.STANDARD: dwn.DEFAULT_RETRY_ATTEMPTS,
            RetryProfile.AGGRESSIVE: (1, 2, 5),
        }[self]


@dataclasses.dataclass(frozen=True)
class Parameters:
    starting_game_id: dwn.GameID
    overwrite_found_files: bool
    target_directory: pathlib.Path
    profile: RetryProfile


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

    profile_name = os.getenv("RETRY_PROFILE", "STANDARD").upper()
    try:
        profile = RetryProfile[profile_name]
    except KeyError:
        profile = RetryProfile.STANDARD

    return Parameters(starting_game_id, overwrite_found_files, target_dir, profile)


def get_filename(
    target_dir: pathlib.Path, game_id: dwn.GameID
) -> tuple[str, pathlib.Path]:
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

    downloader = dwn.PatchDownloader(
        retry_time_in_seconds=params.profile.retry_timers(),
        game_filter_predicate=game_filter(params),
    )

    for game in downloader.download_patch(params.starting_game_id):
        filename, destination = get_filename(params.target_directory, game.game_id)

        if isinstance(
            game,
            (
                dwn.DownloadedGame,
                dwn.FailedDownloadAttempt,
                dwn.MismatchedPatchDownloadAttempt,
            ),
        ):
            with open(destination, "wb") as game_file:
                raw_bytes = game.response.content
                game_file.write(raw_bytes)
            logger.info(f"Written bytes=<{len(raw_bytes)}> to filename=<{filename}>")


if __name__ == "__main__":
    main()
