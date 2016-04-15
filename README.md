Installation:
-------------

* git clone this repo
* create a `conf.toml` file (you can use `example_conf.toml` as a base)
  * craete a bot: http://telegram.me/botfather, use the bot's token in the config
  * obtain a chat id for your account: contact http://telegram.me/myidbot

Execution:
----------
* from the directory where `conf.toml` is located execute `inform.py` (python 3.4 is required)


Configuring Sonarr:
-------------------
* From `System -> Connections` add a new connection/notification of type `webhook`.
* URL is: http://`<IP>`:8080/sonarr
* METHOD is: POST
