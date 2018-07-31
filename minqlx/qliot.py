import minqlx
import threading
import re
import os
import time

from Adafruit_IO import *

# Set to your Adafruit IO key & username below.
ADAFRUIT_IO_KEY = '23e6038612264843b38d1b7f8a54c808'
ADAFRUIT_IO_USERNAME = 'lucote'

INTERESTING_GAME_TYPES = ['ad', 'ctf']

def connected(client):
  print('Connected to Adafruit IO! Listening for updates...')
  client.subscribe('qliot')

def disconnected(client):
  print('Disconnected from Adafruit IO!')
  #sys.exit(1)

def message(client, feed_id, payload):
  #print('Feed {0} received new value: {1}'.format(feed_id, payload))
  pass

class qliot(minqlx.Plugin):
  def __init__(self):
    self.add_hook('player_loaded', self.handle_player_loaded)
    self.add_hook('player_disconnect', self.handle_player_disconnect)
    self.client = MQTTClient(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
    self.client.on_connect = connected
    self.client.on_disconnect = disconnected
    self.client.on_message = message
    self.client.connect()
    self.client.loop_background()

  def is_interesting_game_type(self):
    return self.game.type_short in INTERESTING_GAME_TYPES

  def publish(self, msg):
    self.client.publish('qliot', msg)

  def handle_player_disconnect(self, player, reason):
    if (player.steam_id == 76561198282206581):
      self.running = False

  def handle_player_loaded(self, player):
    if (player.steam_id == 76561198282206581):
      self.running = True
      threading.Thread(target=self.send_position, args=(player,)).start()

  def send_position(self, player):
    while self.running:
      if (player.state.position.x < 0):
        self.publish('r')
      else:
        self.publish('b')
      time.sleep(2)
