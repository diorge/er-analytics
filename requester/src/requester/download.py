import dataclasses
import itertools
import time
import typing

import ratelimit
import requests
from loguru import logger

GameID = typing.NewType("GameID", int)

CALLS_PER_SECOND: int = 1
DEFAULT_RETRY_ATTEMPTS = (0, 1, 2, 5, 10, 30)


class TooManyTriesError(Exception):
    pass


@ratelimit.sleep_and_retry
@ratelimit.limits(calls=CALLS_PER_SECOND, period=1)
def get_game_data(
    game_id: GameID,
    api_token: typing.Optional[str] = None,
    url: str = "https://open-api.bser.io/v1/games",
) -> requests.Response:
    """Download all the data of a single match."""

    if api_token is None:
        with open("key.secret", "r") as f:
            api_token = f.read()

    headers = {"x-api-key": api_token, "accept": "application/json"}
    complete_url = f"{url}/{game_id}"

    logger.debug(f"Requesting game_id=<{game_id}>")
    response = requests.get(complete_url, headers=headers)

    return response


def get_patch(game_data: typing.Dict[str, typing.Any]) -> typing.Tuple[str, str]:
    first_player = game_data["userGames"][0]
    patch_version = first_player["versionMajor"]
    hotfix_version = first_player["versionMinor"]
    return (patch_version, hotfix_version)


@dataclasses.dataclass
class DownloadedGame:
    game_id: GameID
    data: typing.Dict[str, typing.Any]
    raw: bytes


def download_patch(
    starting_game_id: GameID,
    retry_time_in_seconds: typing.Tuple[float, ...] = DEFAULT_RETRY_ATTEMPTS,
) -> typing.Iterable[DownloadedGame]:
    """
    Downloads game matches from the patch of the given Game ID.
    Will keep downloading at time intervals upon reaching 404 (or any error),
    since it should be downloading the most current matches.
    When moving forward it will also keep patch in mind,
    not stepping boundaries into the next patch.
    """

    starting_game = get_game_data(starting_game_id)
    yield DownloadedGame(starting_game_id, starting_game.json(), starting_game.content)

    target_patch = get_patch(starting_game.json())

    def download_from(game_id_seq):
        current_patch = target_patch

        while current_patch == target_patch:
            next_id = next(game_id_seq)

            attempt = 0
            successful = False
            while not successful and attempt < len(retry_time_in_seconds):
                time.sleep(retry_time_in_seconds[attempt])
                next_game = get_game_data(GameID(next_id))
                successful = (
                    next_game.status_code == 200 and next_game.json()["code"] == 200
                )
                attempt += 1
            if not successful:
                raise TooManyTriesError(
                    f"Maximum attempts at retrieving game data for game_id=<{next_id}>"
                )

            current_patch = get_patch(next_game.json())
            if current_patch == target_patch:
                yield DownloadedGame(next_id, next_game.json(), next_game.content)

    yield from download_from(itertools.count(start=starting_game_id - 1, step=-1))
    yield from download_from(itertools.count(start=starting_game_id + 1))
