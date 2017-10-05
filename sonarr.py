import enum

from typing import List


def _get_key(info: dict, keys: List[str]):
    for key in (x for x in keys if x in info):
        return info[key]
    else:
        raise Exception('Missing {}', keys[0])


class Payload():

    def __init__(self, msg: dict):
        self.type = EventType(_get_key(msg, ['EventType', 'eventType']).capitalize())
        self.series = Series(_get_key(msg, ['Series', 'series']))
        episodes = _get_key(msg, ['Episodes', 'episodes'])
        self.episodes = [Episode(x) for x in episodes if episodes]


class EventType(enum.Enum):
    download = 'Download'
    grab = 'Grab'
    rename = 'Rename'
    test = 'Test'


class Series():

    def __init__(self, info: dict):
        self.title = _get_key(info, ['Title', 'title'])
        self.tvdb_id = _get_key(info, ['TvdbId', 'tvdbId'])


class Episode():

    def __init__(self, info: dict):
        self.num = _get_key(info, ['EpisodeNumber', 'episodeNumber'])
        self.season = _get_key(info, ['SeasonNumber', 'seasonNumber'])
        self.title = _get_key(info, ['Title', 'title'])
        self.quality = _get_key(info, ['Quality', 'quality'])
