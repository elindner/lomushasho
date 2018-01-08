import json
import sys
import unittest
import minqlx_fake
import trueskill_fake

from unittest.mock import mock_open
from unittest.mock import patch

sys.modules['minqlx'] = minqlx_fake
sys.modules['trueskill'] = trueskill_fake
import oloraculo

PLAYER = {}
CHANNEL = {}

class TestOloraculo(unittest.TestCase):
  def setUp(self):
    minqlx_fake.reset()


  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_registers_commands_and_hooks(self):
    olor = oloraculo.oloraculo()
    self.assertEqual([
        'oloraculo',
        'oloraculo_ratings'],
        sorted([cmd[0] for cmd in minqlx_fake.Plugin.registered_commands]))

    self.assertEqual([
        'game_end',
        'game_start',
        'player_loaded'],
        sorted([hook[0] for hook in minqlx_fake.Plugin.registered_hooks]))


  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_handles_player_loaded(self):
    olor = oloraculo.oloraculo()
    self.assertEqual(set(), olor.get_stats().get_player_ids('ad'))
    player = minqlx_fake.Player(123456, 'sarge')
    olor.handle_player_loaded(player)
    self.assertEqual({123456}, olor.get_stats().get_player_ids('ad'))
    self.assertEqual([0, 0], olor.get_stats().get_winloss('ad', 123456))
    self.assertEqual([0, 0], olor.get_stats().get_killdeath('ad', 123456))



if __name__ == '__main__':
    unittest.main()
