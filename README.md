Prerequisites:
--------------
* Python3.4 or above

Installation:
-------------

* git clone this repo
* Insure that all requirements are met:
  * issue: `# pip3 install $(< requirements.txt)`
* create a `conf.toml` file (you can use `example_conf.toml` as a base)
  * craete a bot: http://telegram.me/botfather, use the bot's token in the config
  * obtain a chat id for your account: contact http://telegram.me/myidbot
    * The chat id will be used to know to which chat to send the messages to.
    * The best thing to do is create a group and add @myidbot to the chat.

Execution:
----------
* Check the usage help of the tool: `# ./inform.py -h`
* A minimal requirement is having a valid *toml* configuration file.
By default the **inform.py** looks for `./conf.toml`

Configuring Sonarr:
-------------------
* From `System -> Connections` add a new connection/notification of type `webhook`.
* URL is: http://`<IP>`:8080/sonarr
* METHOD is: POST