# Eternal Return Analytics

Game history macro analytics for [Eternal Return (free on Steam)](https://playeternalreturn.com).

This project consists of downloading match history data from the official API,
building a local data warehouse offline,
and drawing insights from this data on a macro level
(relative character strength, matchups, killzones and so on).

## Official ER API

The [official API](https://developer.eternalreturn.io/) requires a key to perform the HTTP requests
(you would need to request a key to reproduce the results).
The route this project concerns is `v1/games/{game_id}`.