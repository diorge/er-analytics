import itertools
import time
import typing

import pytest
import requests_mock

import requester.download as dwn

SAMPLE_GAME_ID = dwn.GameID(13594270)

PatchDownloader = typing.Callable[..., typing.Iterable[dwn.DownloadedGame]]


@pytest.fixture
def unlimited_download_patch() -> PatchDownloader:
    def inner(
        starting_game_id: dwn.GameID,
        *,
        on_error_policy: dwn.OnErrorPolicy = dwn.raise_on_error_policy,
        is_id_valid: typing.Callable[[dwn.GameID], bool] = (lambda _: True),
    ) -> typing.Iterable[dwn.DownloadedGame]:
        return dwn.download_patch(
            starting_game_id,
            retry_time_in_seconds=(0,),
            on_error_policy=on_error_policy,
            is_id_valid=is_id_valid,
            downloader=dwn._download_game_unlimited,
        )

    return inner


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


def test_download_entire_patch(unlimited_download_patch: PatchDownloader) -> None:
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

        gen = []
        try:
            for game in unlimited_download_patch(
                dwn.GameID(11),
            ):
                gen.append(game)
        except dwn.TooManyTriesError:
            pass

        assert 3 == len(gen)


def test_download_stops_next_patch(unlimited_download_patch: PatchDownloader) -> None:
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

        gen = []
        for game in unlimited_download_patch(dwn.GameID(11)):
            gen.append(game)

        assert 3 == len(gen)


def test_skip_policy(unlimited_download_patch: PatchDownloader) -> None:
    """Skip policy will jump over an unretrievable game."""
    fine_json = {"code": 200, "userGames": [{"versionMajor": 45, "versionMinor": 0}]}
    old_json = {"code": 200, "userGames": [{"versionMajor": 44, "versionMinor": 0}]}
    fail_json = {"code": 404}
    with requests_mock.Mocker() as m:
        m.get("https://open-api.bser.io/v1/games/9", json=old_json | {"id": 9})
        m.get("https://open-api.bser.io/v1/games/10", json=fine_json | {"id": 10})
        m.get("https://open-api.bser.io/v1/games/11", json=fail_json | {"id": 11})
        m.get("https://open-api.bser.io/v1/games/12", json=fine_json | {"id": 12})
        m.get("https://open-api.bser.io/v1/games/13", json=fine_json | {"id": 13})

        gen = unlimited_download_patch(
            dwn.GameID(10),
            on_error_policy=dwn.skip_on_error_policy,
        )
        games = itertools.islice(gen, 3)
        assert {10, 12, 13} == {g.data["id"] for g in games}


def test_filter_download_predicate(unlimited_download_patch: PatchDownloader) -> None:
    """Can filter out certain game IDs."""
    fine_json = {"code": 200, "userGames": [{"versionMajor": 45, "versionMinor": 0}]}
    old_json = {"code": 200, "userGames": [{"versionMajor": 44, "versionMinor": 0}]}
    with requests_mock.Mocker() as m:
        m.get("https://open-api.bser.io/v1/games/9", json=old_json | {"id": 9})
        m.get("https://open-api.bser.io/v1/games/10", json=fine_json | {"id": 10})
        m.get("https://open-api.bser.io/v1/games/11", json=fine_json | {"id": 11})
        m.get("https://open-api.bser.io/v1/games/12", json=fine_json | {"id": 12})
        m.get("https://open-api.bser.io/v1/games/13", json=fine_json | {"id": 13})

        gen = unlimited_download_patch(
            dwn.GameID(10),
            is_id_valid=(lambda gid: gid != 11),
        )
        games = itertools.islice(gen, 3)
        assert {10, 12, 13} == {g.data["id"] for g in games}


def test_download_invalid_patch(unlimited_download_patch: PatchDownloader) -> None:
    """Stops at an invalid patch."""
    fine_json = {"code": 200, "userGames": [{"versionMajor": 45, "versionMinor": 0}]}
    invalid_patch = {"code": 200, "userGames": [{}]}
    invalid_userGames = {"code": 200}
    with requests_mock.Mocker() as m:
        m.get("https://open-api.bser.io/v1/games/9", json=invalid_patch | {"id": 9})
        m.get("https://open-api.bser.io/v1/games/10", json=fine_json | {"id": 10})
        m.get(
            "https://open-api.bser.io/v1/games/11", json=invalid_userGames | {"id": 11}
        )

        gen = unlimited_download_patch(dwn.GameID(10))

        assert {10} == {g.data["id"] for g in tuple(gen)}
