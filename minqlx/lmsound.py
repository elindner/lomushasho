import copy
import json
import minqlx
import os
import re
import time

HEADER_COLOR_STRING = '^2'

JSON_FILE_NAME = 'lmsound_map.json'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_FILE_PATH = os.path.join(ROOT_PATH, JSON_FILE_NAME)


class lmsound(minqlx.Plugin):

  def __init__(self):
    super().__init__()
    self.add_hook("chat", self.handle_chat)
    self.add_command('lmsound', self.cmd_lmsound, 1)

    self.last_sound = None

    self.trigger_to_sound = {}
    self.sound_to_triggers = {}
    self.load_sound_map()

  def print_log(self, msg):
    self.msg('%s]v[sound:^7 %s' % (HEADER_COLOR_STRING, msg))

  def print_error(self, msg):
    self.msg('%s]v[sound:^1 %s' % (HEADER_COLOR_STRING, msg))

  def load_sound_map(self):
    try:
      self.set_sound_map(json.loads(open(JSON_FILE_PATH).read()))
      self.print_log('Loaded sounds map with %s keys.' %
                     len(self.sound_to_triggers.keys()))
    except Exception as e:
      self.print_error('Could not load sound map (%s)' % e)

  def set_sound_map(self, sound_map):
    self.sound_to_triggers = copy.deepcopy(sound_map)
    self.trigger_to_sound = {}
    for sound in sound_map:
      self.sound_to_triggers[sound].append(sound)
      self.trigger_to_sound[sound] = sound
      for trigger in sound_map[sound]:
        self.trigger_to_sound[trigger] = sound

  def play_sound_trigger(self, path):
    if not self.last_sound:
      pass
    elif time.time() - self.last_sound < self.get_cvar("qlx_funSoundDelay",
                                                       int):
      return

    self.last_sound = time.time()
    for p in self.players():
      if self.db.get_flag(p, "essentials:sounds_enabled", default=True):
        self.play_sound(path, p)

  def handle_chat(self, player, msg, channel):
    if channel != "chat":
      return

    msg = self.clean_text(msg)
    if msg in self.trigger_to_sound:
      self.play_sound_trigger('sound/lm/%s.ogg' % self.trigger_to_sound[msg])

  def cmd_lmsound(self, player, msg, channel):
    player.tell('%s%s' % (HEADER_COLOR_STRING, '=' * 80))
    player.tell('%s]v[sound v0.0.0.0.1h:^7' % HEADER_COLOR_STRING)
    player.tell('%s%s' % (HEADER_COLOR_STRING, '-' * 80))

    if len(self.sound_to_triggers.keys()) == 0:
      player.tell('No sounds mapped!')
      return

    longest_sound = max([len(x) for x in self.trigger_to_sound])
    fmt_string = "  ^3%%%ds^7: %%s" % longest_sound

    lines = []
    for sound in sorted(self.sound_to_triggers.keys()):
      lines.append(fmt_string %
                   (sound, ', '.join(sorted(self.sound_to_triggers[sound]))))
    player.tell('\n'.join(lines))
