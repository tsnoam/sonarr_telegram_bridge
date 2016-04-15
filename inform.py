#!/usr/bin/python3
import logging
import threading
from queue import Queue

import cherrypy
import telegram
import telegram.error
import time
import toml
from pytvdbapi.error import BadData

import tv_info
from sonarr import Payload, Episode, Series, EventType


TELEGRAM_TEMPLATE = '''{title} S{season:02d}E{ep:02d} ({quality})
{action}

{overview}

{banner}'''


class CRUDListener():

    def __init__(self, episodes_q: Queue):
        self.queue = episodes_q

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def sonarr(self):
        msg = cherrypy.request.json
        payload = Payload(msg)

        for i in payload.episodes:
            msg = EpisodeMsg(payload.series, i, payload.type, None)
            self.queue.put(msg)


class EnhanceEpisodeInfo():

    def __init__(self, episodes_q: Queue, telegram_q: Queue, logger: logging.Logger):
        self.in_q = episodes_q
        self.out_q = telegram_q
        self.tvdb = tv_info.init_tvdb()
        self.logger = logger

    def run(self):
        while 1:
            msg = self.in_q.get()
            """:type: EpisodeMsg"""
            info = self._get_episode_info(msg.series.tvdb_id, msg.episode)
            if info:
                msg.info = info
                self.out_q.put(msg)

    def _get_episode_info(self, tvdb_id: int, episode: Episode) -> tv_info.EpisodeInfo:
        attempt = 1
        sleep_tm = 1

        while 1:
            try:
                return tv_info.EpisodeInfo(self.tvdb, tvdb_id, episode.season, episode.num)

            except (ConnectionError, BadData):
                self.logger.warning(
                    'tvdb server in trouble; attempt={} sleep={}'.format(attempt, sleep_tm),
                    exc_info=True)
                time.sleep(sleep_tm)
                attempt += 1
                if sleep_tm < 60:
                    sleep_tm *= 2

            except Exception:
                self.logger.exception('unknown error')
                return


class EpisodeMsg():
    def __init__(self, series: Series, episode: Episode, event_type: EventType,
                 info: tv_info.EpisodeInfo):
        self.series = series
        self.episode = episode
        self.info = info
        self.type = event_type


class SendTelegrams():

    def __init__(self, tg_queue: Queue, bot: telegram.Bot, chat_ids: [int],
                 logger: logging.Logger):
        self.tg_queue = tg_queue
        self.bot = bot
        self.chat_ids = chat_ids
        self.logger = logger

    def run(self):
        while 1:
            msg = self.tg_queue.get()
            """:type: EpisodeMsg"""
            txt = self._gen_text(msg)
            self.send_tg(txt)

    def send_tg(self, msg: str):
        for i in self.chat_ids:
            attempt = 1
            sleep_tm = 1
            while 1:
                try:
                    self.bot.sendMessage(i, msg, parse_mode='Markdown')

                except telegram.error.NetworkError:
                    self.logger.warning(
                        'telegram servers in trouble; attempt={} sleep={}'.format(
                            attempt, sleep_tm))
                    time.sleep(sleep_tm)
                    attempt += 1
                    if sleep_tm < 60:
                        sleep_tm *= 2
                    continue

                except telegram.TelegramError:
                    self.logger.exception('failed sending telegram')

                break

    @staticmethod
    def _gen_text(msg: EpisodeMsg):
        if msg.type is EventType.grab:
            action = 'Starting download'
        elif msg.type is EventType.download:
            action = 'Finished downloading'
        else:
            action = 'Unknown action'

        return TELEGRAM_TEMPLATE.format(
            title=msg.series.title,
            season=msg.episode.season,
            ep=msg.episode.num,
            quality=msg.episode.quality,
            action=action,
            overview=msg.info.overview,
            banner=msg.info.banner_url)


def main():
    conf = toml.load('conf.toml')
    token = conf['global']['token']
    chat_ids = conf['global']['chat_ids']

    bot = telegram.Bot(token)
    episodes_q = Queue()
    tg_q = Queue()
    logging.basicConfig()
    logger = logging.getLogger()

    crud = CRUDListener(episodes_q)
    eei = EnhanceEpisodeInfo(episodes_q, tg_q, logger)
    cons = SendTelegrams(tg_q, bot, chat_ids, logger)

    threads = [threading.Thread(target=cons.run),
               threading.Thread(target=eei.run)]
    for i in threads:
        i.start()

    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.quickstart(crud)

    for i in threads:
        i.join()


if __name__ == '__main__':
    main()
