"""Package constants: OGS endpoints and URL builders."""

OGS_API_URL = "https://online-go.com/api/v1"
OGS_WEB_URL = "https://online-go.com"


def game_web_url(game_id: int) -> str:
    """Public OGS page of a game."""
    return f"{OGS_WEB_URL}/game/{game_id}"


def game_api_url(game_id: int) -> str:
    """OGS REST endpoint holding the game payload."""
    return f"{OGS_API_URL}/games/{game_id}"
