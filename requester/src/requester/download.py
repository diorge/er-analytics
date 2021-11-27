import dataclasses
import itertools
import time
import typing

import ratelimit
import requests
from loguru import logger

GameID = typing.NewType("GameID", int)
PatchVersion = typing.NewType("PatchVersion", tuple[str, str])

CALLS_PER_SECOND = 1
DEFAULT_RETRY_ATTEMPTS = (0, 1, 2, 5, 10, 30)


@dataclasses.dataclass(frozen=True)
class DownloadResult:
    game_id: GameID


@dataclasses.dataclass(frozen=True)
class DownloadedGame(DownloadResult):
    data: dict[str, typing.Any]
    response: requests.Response


@dataclasses.dataclass(frozen=True)
class FailedDownloadAttempt(DownloadResult):
    attempt_number: int
    response: requests.Response


@dataclasses.dataclass(frozen=True)
class SkippedDownloadAttempt(DownloadResult):
    pass


@dataclasses.dataclass(frozen=True)
class MismatchedPatchDownloadAttempt(DownloadResult):
    game_patch: typing.Optional[PatchVersion]
    expected_patch: PatchVersion
    response: requests.Response


Downloader = typing.Callable[..., requests.Response]


def get_patch(game_data: dict[str, typing.Any]) -> typing.Optional[PatchVersion]:
    first_player = game_data.get("userGames", [{}])[0]
    patch_version = first_player.get("versionMajor")
    hotfix_version = first_player.get("versionMinor")
    if patch_version is not None and hotfix_version is not None:
        return PatchVersion((patch_version, hotfix_version))
    return None


@ratelimit.sleep_and_retry
@ratelimit.limits(calls=CALLS_PER_SECOND, period=1)
def download_game(
    game_id: GameID,
    api_token: typing.Optional[str] = None,
    url: str = "https://open-api.bser.io/v1/games",
) -> requests.Response:
    """
    Downloads the data of a given match, bounded by the API call request limit.
    """
    return _download_game_unlimited(game_id, api_token, url)


def _download_game_unlimited(
    game_id: GameID,
    api_token: typing.Optional[str] = None,
    url: str = "https://open-api.bser.io/v1/games",
) -> requests.Response:
    """
    Downloads the data of a given match, IGNORING API call request limit.
    Only use in the test suite!
    """
    if api_token is None:
        with open("key.secret", "r") as f:
            api_token = f.read()

    headers = {"x-api-key": api_token, "accept": "application/json"}
    complete_url = f"{url}/{game_id}"

    logger.debug(f"Requesting game_id=<{game_id}>")
    response = requests.get(complete_url, headers=headers)

    return response


class PatchDownloader:
    def __init__(
        self,
        *,
        retry_time_in_seconds: tuple[float, ...] = DEFAULT_RETRY_ATTEMPTS,
        game_filter_predicate: typing.Callable[[GameID], bool] = (lambda _: True),
        downloader: Downloader = download_game,
    ):
        self.retry_time_in_seconds = retry_time_in_seconds
        self.game_filter_predicate = game_filter_predicate
        self.downloader = downloader

    def download_patch(
        self, starting_game_id: GameID
    ) -> typing.Iterable[DownloadResult]:
        # force download of starting game to get patch
        starting_game = self._attempt_download(starting_game_id, ignore_skip=True)

        if not isinstance(starting_game, DownloadedGame):
            raise ValueError()

        expected_patch = get_patch(starting_game.data)
        if expected_patch is None:
            raise ValueError()

        yield starting_game

        def yield_seq(
            game_ids: typing.Iterator[GameID],
        ) -> typing.Iterable[DownloadResult]:
            for gid in game_ids:
                result = self._attempt_download(gid, expected_patch)
                yield result
                if isinstance(result, MismatchedPatchDownloadAttempt):
                    break

        backwards_ids = map(
            GameID, itertools.count(start=starting_game_id - 1, step=-1)
        )
        forward_ids = map(GameID, itertools.count(start=starting_game_id + 1))

        yield from yield_seq(backwards_ids)
        yield from yield_seq(forward_ids)

    def _attempt_download(
        self,
        game_id: GameID,
        expected_patch: typing.Optional[PatchVersion] = None,
        *,
        ignore_skip: bool = False,
    ) -> DownloadResult:
        if not ignore_skip and not self.game_filter_predicate(game_id):
            logger.info(
                f"Skipping download of game_id=<{game_id}>"
                ", reason=<Predicate filtered>"
            )
            return SkippedDownloadAttempt(game_id)

        max_attempts = len(self.retry_time_in_seconds)
        attempt = 0
        successful = False
        while not successful and attempt < max_attempts:
            game_resp = self.downloader(game_id)
            successful = (
                game_resp.status_code == 200 and game_resp.json()["code"] == 200
            )
            if not successful:
                time.sleep(self.retry_time_in_seconds[attempt])
                attempt += 1

        if not successful:
            logger.info(
                f"Reached maximum attempts=<{attempt}>"
                f" for downloading game_id=<{game_id}>"
            )
            return FailedDownloadAttempt(game_id, attempt, game_resp)

        game_data = game_resp.json()
        game_patch = get_patch(game_data)
        if game_patch is None:
            logger.warning(f"Unable to retrieve patch for game_id=<{game_id}>")

        if expected_patch is not None and expected_patch != game_patch:
            return MismatchedPatchDownloadAttempt(
                game_id, game_patch, expected_patch, game_resp
            )

        return DownloadedGame(game_id, game_data, game_resp)
