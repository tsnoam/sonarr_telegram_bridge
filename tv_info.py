from pytvdbapi import api


class EpisodeInfo():

    def __init__(self, db: api.TVDB, show_id: int, season: int, episode: int):
        self._db = db

        self._show = self._db.get_series(show_id, 'en')
        self._show.update()
        self._show.load_banners()

        self._episode = self._show[season][episode]

    @property
    def banner_url(self):
        if not self._show.banner_objects:
            return None

        # arbitrary select the first banner
        return self._show.banner_objects[0].banner_url

    @property
    def overview(self):
        return self._episode.Overview


def init_tvdb(api_key='0629B785CE550C8D') -> api.TVDB:
    return api.TVDB(api_key)
