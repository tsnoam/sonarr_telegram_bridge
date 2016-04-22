#!/usr/bin/python3
import logging
import threading
import time
import argparse
from queue import Queue, Empty

import cherrypy
import signal
import telegram
import telegram.error
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
        self._logger = logger.getChild(self.__class__.__name__)
        self._stop_execution = threading.Event()

    def run(self):
        while not self._stop_execution.is_set():
            try:
                msg = self.in_q.get(block=False, timeout=1)
                """:type: EpisodeMsg"""
            except Empty:
                continue
            if not msg:
                continue
            info = self._get_episode_info(msg.series.tvdb_id, msg.episode)
            if info:
                msg.info = info
                self.out_q.put(msg)

    def stop(self):
        self._logger.info('stopping')
        self._stop_execution.set()

    def _get_episode_info(self, tvdb_id: int, episode: Episode) -> tv_info.EpisodeInfo:
        attempt = 1
        sleep_tm = 1

        while 1:
            try:
                return tv_info.EpisodeInfo(self.tvdb, tvdb_id, episode.season, episode.num)

            except (ConnectionError, BadData):
                self._logger.warning(
                    'tvdb server in trouble; attempt={} sleep={}'.format(attempt, sleep_tm),
                    exc_info=True)
                time.sleep(sleep_tm)
                attempt += 1
                if sleep_tm < 60:
                    sleep_tm *= 2

            except Exception:
                self._logger.exception('unknown error')
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
        self._logger = logger.getChild(self.__class__.__name__)
        self._stop_execution = threading.Event()

    def run(self):
        while not self._stop_execution.is_set():
            try:
                msg = self.tg_queue.get(block=True, timeout=1)
                """:type: EpisodeMsg"""
            except Empty:
                continue
            txt = self._gen_text(msg)
            self.send_tg(txt)

    def stop(self):
        self._logger.info('stopping')
        self._stop_execution.set()

    def send_tg(self, msg: str):
        for i in self.chat_ids:
            attempt = 1
            sleep_tm = 1
            while 1:
                try:
                    self.bot.sendMessage(i, msg, parse_mode='Markdown')

                except telegram.error.NetworkError:
                    self._logger.warning(
                        'telegram servers in trouble; attempt={} sleep={}'.format(
                            attempt, sleep_tm))
                    time.sleep(sleep_tm)
                    attempt += 1
                    if sleep_tm < 60:
                        sleep_tm *= 2
                    continue

                except telegram.TelegramError:
                    self._logger.exception('failed sending telegram')

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


class CherrypyWrapper():

    def __init__(self, app, logger: logging.Logger, port: int):
        self._logger = logger.getChild(self.__class__.__name__)
        self._app = app
        self._port = port

    def run(self):
        cherrypy.server.socket_host = '0.0.0.0'
        cherrypy.server.socket_port = self._port
        cherrypy.tree.mount(self._app)
        cherrypy.engine.start()
        cherrypy.engine.block()

    def stop(self):
        self._logger.info('stopping')
        cherrypy.engine.exit()


class SignalHandler():

    def __init__(self, stoppable: list, logger: logging.Logger):
        self._stoppable = stoppable
        self._logger = logger
        signal.signal(signal.SIGINT, self.handle)
        signal.signal(signal.SIGTERM, self.handle)

    def handle(self, signum, _stack_frame):
        self._logger.info('caught signal {}: terminating'.format(signum))
        for i in self._stoppable:
            i.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--conf",
                        help="Configuration file; (default: ./conf.toml)",
                        default="conf.toml")
    parser.add_argument("-p", "--port",
                        help="Local port to listen to; (default: 8080)",
                        default=8080,
                        type=int)
    args = parser.parse_args()

    conf_file = args.conf
    port = args.port

    conf = toml.load(conf_file)

    token = conf['global']['token']
    chat_ids = conf['global']['chat_ids']

    bot = telegram.Bot(token)
    episodes_q = Queue()
    tg_q = Queue()
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()

    crud = CRUDListener(episodes_q)
    eei = EnhanceEpisodeInfo(episodes_q, tg_q, logger)
    cons = SendTelegrams(tg_q, bot, chat_ids, logger)
    cherry = CherrypyWrapper(crud, logger, port)

    SignalHandler([eei, cons, cherry], logger)

    threads = [threading.Thread(target=cons.run),
               threading.Thread(target=eei.run),
               threading.Thread(target=cherry.run)]

    for i in threads:
        i.start()

    for i in threads:
        i.join()

    logger.info('finished')


if __name__ == '__main__':
    main()
