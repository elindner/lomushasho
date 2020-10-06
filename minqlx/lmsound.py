import copy
import minqlx
import re
import time

HEADER_COLOR_STRING = '^2'

# Move this to json config?
SOUND_MAP = {
    '415': [],
    'alacamita': [
        'topo',
        'gigio',
        'topogigio',
    ],
    'aplausos': ['clapclapclap',],
    'apunt': [],
    'chan': ['drama',],
    'corrupt': [],
    'cuac': ['pato',],
    'english': ['inglish',],
    'eldiego': ['eeeee',],
    'eltiburon': ['tibuton',],
    'fatality': ['mk',],
    'grillos': ['cricricri',],
    'hallelujah': ['aleluya',],
    'hastalavista': ['arnold',],
    'illbeback': ['back',],
    'japush': [
        'pina',
        'punch',
    ],
    'jaws': [],
    'mastarde': [],
    'modem': [],
    'stopit': [],
    'vader': ['soytupadre',],
    'vivaperon': ['peron',],
    'xfiles': [],
}


class lmsound(minqlx.Plugin):

  def __init__(self):
    super().__init__()
    self.add_hook("chat", self.handle_chat)
    self.add_command('lmsound', self.cmd_lmsound, 1)

    self.last_sound = None

    self.trigger_to_sound = {}
    self.sound_to_triggers = {}
    self.set_sound_map(SOUND_MAP)

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

    longest_sound = max([len(x) for x in self.trigger_to_sound])
    fmt_string = "  ^3%%%ds^7: %%s" % longest_sound

    for sound in sorted(self.sound_to_triggers.keys()):
      # triggers = ', '.join(sorted(self.trigger_to_sound[sound]))
      player.tell(fmt_string %
                  (sound, ', '.join(sorted(self.sound_to_triggers[sound]))))
