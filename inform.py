#!/usr/bin/python3
import logging
import threading
from queue import Queue

import cherrypy
import telegram
import telegram.error
import toml

from sonarr import Payload


class Producer():

    def __init__(self, tg_queue: Queue):
        self.tg_queue = tg_queue

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def sonarr(self):
        msg = cherrypy.request.json
        payload = Payload(msg)
        tgmsgs = create_tg_sonarr_msgs(payload)
        for i in tgmsgs:
            self.tg_queue.put(i)


def create_tg_sonarr_msgs(payload: Payload):
    for i in range(len(payload.episodes)):
        epi = payload.episodes[i]
        msg = '{title} S{season:02d}E{ep:02d} ({quality})'.format(
            title=payload.series.title,
            season=epi.season,
            ep=epi.num,
            quality=epi.quality)
        yield msg


class Consumer():
    def __init__(self, tg_queue: Queue, bot: telegram.Bot, chat_ids: [int],
                 logger: logging.Logger):
        self.tg_queue = tg_queue
        self.bot = bot
        self.chat_ids = chat_ids
        self.logger = logger

    def run(self):
        while 1:
            msg = self.tg_queue.get()
            self.send_tg(msg)

    def send_tg(self, msg: str):
        for i in self.chat_ids:
            while 1:
                try:
                    self.bot.sendMessage(i, msg, parse_mode='Markdown')
                except telegram.error.NetworkError:
                    continue
                except telegram.TelegramError:
                    self.logger.exception('==>')

                break


def main():
    conf = toml.load('conf.toml')
    token = conf['global']['token']
    chat_ids = conf['global']['chat_ids']

    bot = telegram.Bot(token)
    queue = Queue()
    logging.basicConfig()
    logger = logging.getLogger()

    cons = Consumer(queue, bot, chat_ids, logger)
    prod = Producer(queue)

    thr = threading.Thread(target=cons.run)
    thr.start()

    cherrypy.server.socket_host = '0.0.0.0'
    cherrypy.quickstart(prod)

    thr.join()


if __name__ == '__main__':
    main()
