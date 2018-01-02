import json
import sys
import unittest
import minqlx_fake

from unittest.mock import mock_open
from unittest.mock import patch

sys.modules['minqlx'] = minqlx_fake
import mapuche

PLAYER = {}
CHANNEL = {}
SINGLE_ALIAS_DATA = {'playa': 'q3wcp16'}
MULTI_ALIAS_DATA = {
  'asilo': 'asylum',
  'balcon': '13camp',
  'herradura': 'courtyard',
  'lapidas': 'railyard',
  'patio': 'duelingkeeps',
  'playa': 'q3wcp16',
}

class TestMapuche(unittest.TestCase):
  def setUp(self):
    minqlx_fake.reset()

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_registers_commands(self):
    mapu = mapuche.mapuche()
    self.assertEqual([
        'mapuche',
        'mapuche_aliases',
        'mapuche_reload',
        'mapuche_remove',
        'mapuche_set'],
        sorted([cmd[0] for cmd in minqlx_fake.State.registered_commands]))


  @patch('builtins.open', mock_open(read_data=json.dumps(SINGLE_ALIAS_DATA)))
  def test_loads_aliases(self):
    mapu = mapuche.mapuche()
    print(minqlx_fake.last_message)
    self.assertEqual({'playa': 'q3wcp16'}, mapu.get_aliases())


  @patch('builtins.open', mock_open(read_data=json.dumps(SINGLE_ALIAS_DATA)))
  def test_loads_aliases(self):
    mapu = mapuche.mapuche()
    self.assertEqual(SINGLE_ALIAS_DATA, mapu.get_aliases())


  @patch('builtins.open', mock_open(read_data=json.dumps(SINGLE_ALIAS_DATA)))
  def test_set(self):
    mapu = mapuche.mapuche()
    self.assertEqual(SINGLE_ALIAS_DATA, mapu.get_aliases())
    mapu.cmd_mapuche_set(PLAYER, (None, 'patio', 'duelingkeeps'), CHANNEL)
    self.assertEqual(
        {'playa': 'q3wcp16', 'patio': 'duelingkeeps'}, mapu.get_aliases())


  @patch('builtins.open', mock_open(read_data=json.dumps(MULTI_ALIAS_DATA)))
  def test_remove(self):
    mapu = mapuche.mapuche()
    self.assertEqual(MULTI_ALIAS_DATA, mapu.get_aliases())
    mapu.cmd_mapuche_remove(PLAYER, (None, 'patio'), CHANNEL)
    self.assertEqual({
        'asilo': 'asylum',
        'balcon': '13camp',
        'herradura': 'courtyard',
        'lapidas': 'railyard',
        'playa': 'q3wcp16',
      },
      mapu.get_aliases())


  @patch('builtins.open', mock_open(read_data=json.dumps(MULTI_ALIAS_DATA)))
  def test_change_map(self):
    mapu = mapuche.mapuche()
    self.assertEqual(None, minqlx_fake.State.current_factory)
    self.assertEqual(None, minqlx_fake.State.current_map_name)
    mapu.cmd_mapuche(PLAYER, (None, 'patio', 'ad'), CHANNEL)
    self.assertEqual('ad', minqlx_fake.State.current_factory)
    self.assertEqual(
        MULTI_ALIAS_DATA['patio'], minqlx_fake.State.current_map_name)


if __name__ == '__main__':
    unittest.main()
