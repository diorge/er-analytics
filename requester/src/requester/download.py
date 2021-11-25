import typing

import ratelimit
import requests

GameID = typing.NewType("GameID", int)

CALLS_PER_SECOND: int = 1


@ratelimit.sleep_and_retry
@ratelimit.limits(calls=CALLS_PER_SECOND, period=1)
def get_game_data(
    game_id: GameID,
    api_token: typing.Optional[str] = None,
    url: str = "https://open-api.bser.io/v1/games",
) -> requests.Response:
    if api_token is None:
        with open("key.secret", "r") as f:
            api_token = f.read()

    headers = {"x-api-key": api_token, "accept": "application/json"}
    complete_url = f"{url}/{game_id}"

    response = requests.get(complete_url, headers=headers)

    return response
