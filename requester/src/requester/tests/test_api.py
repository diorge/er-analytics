import time

import requests_mock

import requester.download as dwn


SAMPLE_GAME_ID = dwn.GameID(13594270)


def test_limit_by_clock() -> None:
    """Attempting multiple calls to download game data within 1 second causes a delay."""
    start = time.time()
    # make 5 calls
    with requests_mock.Mocker() as m:
        m.get("https://open-api.bser.io/v1/games/0", json={"code": 200})
        for _ in range(5):
            dwn.get_game_data(dwn.GameID(0))
    end = time.time()

    # at least 4 seconds must have passed, plus a small tolerance
    TOLERANCE = 1.1  # extra 10%
    assert 4 <= (end - start) * TOLERANCE


def test_user_games_retrieved() -> None:
    """The API hits are getting us the user games."""
    # NOTE: avoid having more tests hitting the official API;
    # this one and `test_api_key_invalid` are enough.
    # use mocks instead
    response = dwn.get_game_data(SAMPLE_GAME_ID)
    assert 200 == response.status_code
    players_stats = response.json()["userGames"]
    assert 18 == len(players_stats)


def test_api_key_invalid() -> None:
    """The API requires a valid key."""
    # just a check we're actually hitting the official API with our token
    response = dwn.get_game_data(SAMPLE_GAME_ID, api_token="SomeInvalidToken")
    assert response.status_code == 403
