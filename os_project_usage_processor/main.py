from typing import Optional, List


from aiohttp import web

from .views import hello


def app_init(argv: Optional[List[str]] = None) -> web.Application:
    """
    Function to setup the application. Can also be used via `python -m aiohttp.web ...`
    """
    app = web.Application()
    app.add_routes([web.get(r"/{id}", hello)])

    return app
