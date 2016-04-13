import enum
import json


class Payload():

    def __init__(self, msg: dict):
        self.type = EventType(msg['EventType'])
        self.series = Series(msg['Series'])
        episodes = msg['Episodes']
        self.episodes = [Episode(x) for x in episodes if episodes]


class EventType(enum.Enum):
    download = 'Download'
    grab = 'Grab'
    rename = 'Rename'
    test = 'Test'


class Series():

    def __init__(self, info: dict):
        self.title = info['Title']
        self.tvdb_id = info['TvdbId']


class Episode():

    def __init__(self, info: dict):
        self.num = info['EpisodeNumber']
        self.season = info['SeasonNumber']
        self.title = info['Title']
        self.quality = info['Quality']
