import json
import re
import sys
import unittest
import minqlx_fake

from unittest.mock import mock_open
from unittest.mock import patch

sys.modules['minqlx'] = minqlx_fake
import lmsound

PLAYER = minqlx_fake.Player(10, 'cthulhu')
SOUND_MAP = {
    'dog': ['woof'],
    'cat': ['meow', 'prrrr'],
    'bird': ['tweet'],
    'turtle': [],
}
SOUND_MAP_JSON = json.dumps(SOUND_MAP)


class TestLmsound(unittest.TestCase):

  def setUp(self):
    minqlx_fake.reset()

  def assertInMessages(self, txt):
    self.assertTrue([line for line in PLAYER.messages if txt in line],
                    '"%s" not in messages. Messages: %s' %
                    (txt, '\n'.join(PLAYER.messages)))

  @patch('builtins.open', mock_open(read_data='invalid'))
  def test_loads_map_invalid(self):
    lms = lmsound.lmsound()
    PLAYER.clear_messages()
    minqlx_fake.call_command('!lmsound', PLAYER)
    self.assertInMessages('No sounds mapped!')
    pass

  @patch('builtins.open', mock_open(read_data=SOUND_MAP_JSON))
  def test_prints_triggers(self):
    lms = lmsound.lmsound()
    PLAYER.clear_messages()
    minqlx_fake.call_command('!lmsound', PLAYER)
    self.assertInMessages('  bird: bird, tweet')
    self.assertInMessages('  cat: cat, meow, prrrr')
    self.assertInMessages('  dog: dog, woof')
    self.assertInMessages('  turtle: turtle')

  @patch('builtins.open', mock_open(read_data=SOUND_MAP_JSON))
  def test_play_sound(self):
    lms = lmsound.lmsound()
    lms.set_cvar('qlx_funSoundDelay', 0)
    minqlx_fake.Plugin.set_players_by_team({'red': [PLAYER]})

    minqlx_fake.send_chat(PLAYER, 'no sound')
    minqlx_fake.send_chat(PLAYER, 'bird')
    self.assertEqual(minqlx_fake.Plugin.sounds_played[PLAYER],
                     ['sound/lm/bird.ogg'])
    minqlx_fake.send_chat(PLAYER, 'meow')
    self.assertEqual(minqlx_fake.Plugin.sounds_played[PLAYER],
                     ['sound/lm/bird.ogg', 'sound/lm/cat.ogg'])
    minqlx_fake.send_chat(PLAYER, 'no sound')
    self.assertEqual(minqlx_fake.Plugin.sounds_played[PLAYER],
                     ['sound/lm/bird.ogg', 'sound/lm/cat.ogg'])


if __name__ == '__main__':
  unittest.main()
