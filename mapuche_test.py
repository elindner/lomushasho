import json
import re
import sys
import unittest
import minqlx_fake

from unittest.mock import mock_open
from unittest.mock import patch

sys.modules['minqlx'] = minqlx_fake
import mapuche

SINGLE_ALIAS_DATA = {'playa': {'mapname': 'q3wcp16', 'factory': 'ad'}}
MULTI_ALIAS_DATA = {
    'asilo': {'mapname': 'asylum', 'factory': 'ad'},
    'balcon': {'mapname': '13camp', 'factory': 'ad'},
    'herradura': {'mapname': 'courtyard', 'factory': 'ad'},
    'lapidas': {'mapname': 'railyard', 'factory': 'ad'},
    'patio': {'mapname': 'duelingkeeps', 'factory': 'ctf'},
    'playa': {'mapname': 'q3wcp16', 'factory': 'ad'},
}
SINGLE_ALIAS_JSON = json.dumps(SINGLE_ALIAS_DATA)
MULTI_ALIAS_JSON = json.dumps(MULTI_ALIAS_DATA)


class TestMapuche(unittest.TestCase):
  def setUp(self):
    minqlx_fake.reset()

  def assertSavedJson(self, expected, mocked_open):
    file_handle = mocked_open.return_value.__enter__.return_value
    first_write = file_handle.write.call_args_list[0]
    write_arguments = first_write[0]
    saved_json = write_arguments[0]
    self.assertEqual(expected, json.loads(saved_json))

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_registers_commands(self):
    mapu = mapuche.mapuche()
    self.assertEqual([
        'mapuche',
        'mapuche_aliases',
        'mapuche_reload',
        'mapuche_remove',
        'mapuche_set'],
        sorted([cmd[0] for cmd in minqlx_fake.Plugin.registered_commands]))

  @patch('builtins.open', mock_open(read_data='invalid'))
  def test_loads_aliases_invalid_json(self):
    mapu = mapuche.mapuche()
    self.assertEqual({}, mapu.get_aliases())
    # still usable
    minqlx_fake.call_command(
        mapu.cmd_mapuche_set, 'patio', 'duelingkeeps', 'ctf')
    self.assertEqual(
        {'patio': {'mapname': 'duelingkeeps', 'factory': 'ctf'}},
        mapu.get_aliases())

  @patch('builtins.open', mock_open(read_data=SINGLE_ALIAS_JSON))
  def test_loads_aliases(self):
    mapu = mapuche.mapuche()
    self.assertEqual(SINGLE_ALIAS_DATA, mapu.get_aliases())

  @patch('builtins.open', new_callable=mock_open, read_data=SINGLE_ALIAS_JSON)
  def test_saves_aliases(self, m):
    mapu = mapuche.mapuche()
    self.assertEqual(SINGLE_ALIAS_DATA, mapu.get_aliases())

    mapu.save_aliases()
    self.assertSavedJson(SINGLE_ALIAS_DATA, m)

  @patch('builtins.open', mock_open(read_data=SINGLE_ALIAS_JSON))
  def test_set(self):
    expected = {
        'playa': {'mapname': 'q3wcp16', 'factory': 'ad'},
        'patio': {'mapname': 'duelingkeeps', 'factory': 'ctf'},
    }
    mapu = mapuche.mapuche()
    self.assertEqual(SINGLE_ALIAS_DATA, mapu.get_aliases())
    minqlx_fake.call_command(
        mapu.cmd_mapuche_set, 'patio', 'duelingkeeps', 'ctf')
    self.assertEqual(expected, mapu.get_aliases())

  @patch('builtins.open', new_callable=mock_open, read_data=SINGLE_ALIAS_JSON)
  def test_set_saves(self, m):
    expected = {
        'playa': {'mapname': 'q3wcp16', 'factory': 'ad'},
        'patio': {'mapname': 'duelingkeeps', 'factory': 'ctf'},
    }
    mapu = mapuche.mapuche()
    self.assertEqual(SINGLE_ALIAS_DATA, mapu.get_aliases())
    minqlx_fake.call_command(
        mapu.cmd_mapuche_set, 'patio', 'duelingkeeps', 'ctf')
    self.assertEqual(expected, mapu.get_aliases())
    self.assertSavedJson(expected, m)

  @patch('builtins.open', mock_open(read_data=MULTI_ALIAS_JSON))
  def test_remove(self):
    mapu = mapuche.mapuche()
    self.assertEqual(MULTI_ALIAS_DATA, mapu.get_aliases())
    minqlx_fake.call_command(mapu.cmd_mapuche_remove, 'patio')

    self.assertEqual({
        'asilo': {'mapname': 'asylum', 'factory': 'ad'},
        'balcon': {'mapname': '13camp', 'factory': 'ad'},
        'herradura': {'mapname': 'courtyard', 'factory': 'ad'},
        'lapidas': {'mapname': 'railyard', 'factory': 'ad'},
        'playa': {'mapname': 'q3wcp16', 'factory': 'ad'},
    },
        mapu.get_aliases())

  @patch('builtins.open', mock_open(read_data=MULTI_ALIAS_JSON))
  def test_change_map(self):
    mapu = mapuche.mapuche()
    self.assertEqual(None, minqlx_fake.Plugin.current_factory)
    self.assertEqual(None, minqlx_fake.Plugin.current_map_name)
    # force factory
    minqlx_fake.call_command(mapu.cmd_mapuche, 'patio', 'ad')
    self.assertEqual('ad', minqlx_fake.Plugin.current_factory)
    self.assertEqual(
        MULTI_ALIAS_DATA['patio']['mapname'],
        minqlx_fake.Plugin.current_map_name)
    # default factory
    minqlx_fake.call_command(mapu.cmd_mapuche, 'patio')
    self.assertEqual(
        MULTI_ALIAS_DATA['patio']['factory'],
        minqlx_fake.Plugin.current_factory)
    self.assertEqual(
        MULTI_ALIAS_DATA['patio']['mapname'],
        minqlx_fake.Plugin.current_map_name)

  @patch('builtins.open', mock_open(read_data=MULTI_ALIAS_JSON))
  def test_print_aliases(self):
    mapu = mapuche.mapuche()
    minqlx_fake.call_command(mapu.cmd_mapuche_aliases)

    clean_log = minqlx_fake.Channel.message_log.replace(' ', '')
    for alias, data in MULTI_ALIAS_DATA.items():
      self.assertIn(
          '\n%s:%s(%s)\n' % (alias, data['mapname'], data['factory']),
          clean_log)


if __name__ == '__main__':
  unittest.main()
