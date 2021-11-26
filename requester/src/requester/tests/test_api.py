import itertools
import time
import typing

import pytest
import requests_mock

import requester.download as dwn

SAMPLE_GAME_ID = dwn.GameID(13594270)


@pytest.fixture
def unlimited_downloader() -> dwn.PatchDownloader:
    return dwn.PatchDownloader(
        retry_time_in_seconds=(0,), downloader=dwn._download_game_unlimited
    )


def count_result_instances(
    instances: typing.Iterable[dwn.DownloadResult],
) -> typing.Dict[type, int]:
    counts = expected_instance_count(0, 0, 0, 0)
    for inst in instances:
        counts[type(inst)] += 1
    return counts


def expected_instance_count(
    downloaded: int = 0, skipped: int = 0, failed: int = 0, mismatch_patch: int = 0
) -> typing.Dict[type, int]:
    return {
        dwn.DownloadedGame: downloaded,
        dwn.FailedDownloadAttempt: failed,
        dwn.SkippedDownloadAttempt: skipped,
        dwn.MismatchedPatchDownloadAttempt: mismatch_patch,
    }


def test_limit_by_clock() -> None:
    """Attempting multiple calls to download game data within 1 second causes a delay."""
    start = time.time()
    CALLS_TO_MAKE = 5
    EXPECTED_TIME_TO_PASS = (CALLS_TO_MAKE - 1) * dwn.CALLS_PER_SECOND

    with requests_mock.Mocker() as m:
        m.get("https://open-api.bser.io/v1/games/0", json={"code": 200})

        for _ in range(CALLS_TO_MAKE):
            dwn.download_game(dwn.GameID(0))

    end = time.time()

    TOLERANCE = 1.1  # extra 10% because of timer errors
    assert EXPECTED_TIME_TO_PASS <= (end - start) * TOLERANCE


def test_user_games_retrieved() -> None:
    """The API hits are getting us the user games."""
    # NOTE: avoid having more tests hitting the official API;
    # this one and `test_api_key_invalid` are enough.
    # use mocks instead
    response = dwn.download_game(SAMPLE_GAME_ID)
    assert 200 == response.status_code
    players_stats = response.json()["userGames"]
    assert 18 == len(players_stats)


def test_api_key_invalid() -> None:
    """The API requires a valid key."""
    # just a check we're actually hitting the official API with our token
    response = dwn.download_game(SAMPLE_GAME_ID, api_token="SomeInvalidToken")
    assert response.status_code == 403


def test_download_entire_patch(unlimited_downloader: dwn.PatchDownloader) -> None:
    """Is able to download all games of a patch, not touching other patches."""
    fine_json = {"code": 200, "userGames": [{"versionMajor": 45, "versionMinor": 0}]}
    old_json = {"code": 200, "userGames": [{"versionMajor": 44, "versionMinor": 0}]}
    fail_json = {"code": 404}
    with requests_mock.Mocker() as m:
        m.get("https://open-api.bser.io/v1/games/10", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/11", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/12", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/9", json=old_json)
        m.get("https://open-api.bser.io/v1/games/13", json=fail_json)

        for game in unlimited_downloader.download_patch(dwn.GameID(11)):
            if isinstance(game, dwn.FailedDownloadAttempt):
                break

        five_games = itertools.islice(
            unlimited_downloader.download_patch(dwn.GameID(11)), 5
        )
        expected = expected_instance_count(downloaded=3, failed=1, mismatch_patch=1)
        assert expected == count_result_instances(five_games)


def test_download_stops_next_patch(unlimited_downloader: dwn.PatchDownloader) -> None:
    """Downloading the patch stops if the next game is next patch."""
    fine_json = {"code": 200, "userGames": [{"versionMajor": 45, "versionMinor": 0}]}
    old_json = {"code": 200, "userGames": [{"versionMajor": 44, "versionMinor": 0}]}
    future_json = {"code": 200, "userGames": [{"versionMajor": 45, "versionMinor": 1}]}
    with requests_mock.Mocker() as m:
        m.get("https://open-api.bser.io/v1/games/10", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/11", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/12", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/9", json=old_json)
        m.get("https://open-api.bser.io/v1/games/13", json=future_json)

        games = list(unlimited_downloader.download_patch(dwn.GameID(11)))
        assert 5 == len(games)
        expected = expected_instance_count(downloaded=3, mismatch_patch=2)
        assert expected == count_result_instances(games)


def test_filter_download_predicate(unlimited_downloader: dwn.PatchDownloader) -> None:
    """Can filter out certain game IDs."""
    fine_json = {"code": 200, "userGames": [{"versionMajor": 45, "versionMinor": 0}]}
    old_json = {"code": 200, "userGames": [{"versionMajor": 44, "versionMinor": 0}]}
    with requests_mock.Mocker() as m:
        m.get("https://open-api.bser.io/v1/games/9", json=old_json)
        m.get("https://open-api.bser.io/v1/games/10", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/11", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/12", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/13", json=fine_json)

        unlimited_downloader.game_filter_predicate = lambda gid: gid != 11

        games = itertools.islice(unlimited_downloader.download_patch(dwn.GameID(10)), 5)
        expected = expected_instance_count(downloaded=3, skipped=1, mismatch_patch=1)
        assert expected == count_result_instances(games)


def test_download_invalid_patch(unlimited_downloader: dwn.PatchDownloader) -> None:
    """Stops at an invalid patch."""
    fine_json = {"code": 200, "userGames": [{"versionMajor": 45, "versionMinor": 0}]}
    invalid_patch = {"code": 200, "userGames": [{}]}
    invalid_userGames = {"code": 200}
    with requests_mock.Mocker() as m:
        m.get("https://open-api.bser.io/v1/games/9", json=invalid_patch)
        m.get("https://open-api.bser.io/v1/games/10", json=fine_json)
        m.get("https://open-api.bser.io/v1/games/11", json=invalid_userGames)

        games = itertools.islice(unlimited_downloader.download_patch(dwn.GameID(10)), 3)

        expected = expected_instance_count(downloaded=1, mismatch_patch=2)
        assert expected == count_result_instances(games)
