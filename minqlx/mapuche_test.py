import json
import re
import sys
import unittest
import minqlx_fake

from unittest.mock import mock_open
from unittest.mock import patch

sys.modules['minqlx'] = minqlx_fake
import mapuche

SINGLE_ALIAS_DATA = {
    'playa': {
        'mapname': 'q3wcp16',
        'factory': 'ad',
        'dev': False
    }
}
MULTI_ALIAS_DATA = {
    'playa': {
        'mapname': 'q3wcp16',
        'factory': 'ad',
        'dev': False
    },
    'asilo': {
        'mapname': 'asylum',
        'factory': 'ad',
        'dev': False
    },
    'balcon': {
        'mapname': '13camp',
        'factory': 'ad',
        'dev': True
    },
    'herradura': {
        'mapname': 'courtyard',
        'factory': 'ad',
        'dev': False
    },
    'lapidas': {
        'mapname': 'railyard',
        'factory': 'ad',
        'dev': False
    },
    'patio': {
        'mapname': 'duelingkeeps',
        'factory': 'ctf',
        'dev': False
    },
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

  def assertMessages(self, expected):
    expected_string = '\n'.join([l for l in expected if l])
    actual_string = '\n'.join([l for l in minqlx_fake.Plugin.messages if l])
    self.assertIn(expected_string, actual_string)

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_registers_commands(self):
    mapu = mapuche.mapuche()
    self.assertEqual([
        'mapuche', 'mapuche_aliases', 'mapuche_reload', 'mapuche_remove',
        'mapuche_set'
    ], sorted([cmd[0] for cmd in minqlx_fake.Plugin.registered_commands]))

  @patch('builtins.open', mock_open(read_data='invalid'))
  def test_loads_aliases_invalid_json(self):
    mapu = mapuche.mapuche()
    self.assertEqual({}, mapu.get_aliases())
    # still usable
    minqlx_fake.call_command('!mapuche_set patio duelingkeeps ctf')
    self.assertEqual({
        'patio': {
            'mapname': 'duelingkeeps',
            'factory': 'ctf',
            'dev': False
        }
    }, mapu.get_aliases())

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
        'playa': {
            'mapname': 'q3wcp16',
            'factory': 'ad',
            'dev': False
        },
        'patio': {
            'mapname': 'duelingkeeps',
            'factory': 'ctf',
            'dev': False
        },
    }
    mapu = mapuche.mapuche()
    self.assertEqual(SINGLE_ALIAS_DATA, mapu.get_aliases())
    minqlx_fake.call_command('!mapuche_set patio duelingkeeps ctf')
    self.assertEqual(expected, mapu.get_aliases())
    # No overrides!
    minqlx_fake.call_command('!mapuche_set patio somethingelse ctf')
    self.assertEqual(expected['patio'], mapu.get_aliases()['patio'])

  @patch('builtins.open', mock_open(read_data=SINGLE_ALIAS_JSON))
  def test_set_dev(self):
    expected = {
        'playa': {
            'mapname': 'q3wcp16',
            'factory': 'ad',
            'dev': False
        },
        'patio': {
            'mapname': 'duelingkeeps',
            'factory': 'ctf',
            'dev': True
        },
    }
    mapu = mapuche.mapuche()
    self.assertEqual(SINGLE_ALIAS_DATA, mapu.get_aliases())
    minqlx_fake.call_command('!mapuche_set patio duelingkeeps ctf dev')
    self.assertEqual(expected, mapu.get_aliases())

  @patch('builtins.open', new_callable=mock_open, read_data=SINGLE_ALIAS_JSON)
  def test_set_saves(self, m):
    expected = {
        'playa': {
            'mapname': 'q3wcp16',
            'factory': 'ad',
            'dev': False
        },
        'patio': {
            'mapname': 'duelingkeeps',
            'factory': 'ctf',
            'dev': False
        },
    }
    mapu = mapuche.mapuche()
    self.assertEqual(SINGLE_ALIAS_DATA, mapu.get_aliases())
    minqlx_fake.call_command('!mapuche_set patio duelingkeeps ctf')
    self.assertEqual(expected, mapu.get_aliases())
    self.assertSavedJson(expected, m)

  @patch('builtins.open', mock_open(read_data=MULTI_ALIAS_JSON))
  def test_remove(self):
    mapu = mapuche.mapuche()
    self.assertEqual(MULTI_ALIAS_DATA, mapu.get_aliases())
    minqlx_fake.call_command('!mapuche_remove patio')

    self.assertEqual({
        'asilo': {
            'mapname': 'asylum',
            'factory': 'ad',
            'dev': False
        },
        'balcon': {
            'mapname': '13camp',
            'factory': 'ad',
            'dev': True
        },
        'herradura': {
            'mapname': 'courtyard',
            'factory': 'ad',
            'dev': False
        },
        'lapidas': {
            'mapname': 'railyard',
            'factory': 'ad',
            'dev': False
        },
        'playa': {
            'mapname': 'q3wcp16',
            'factory': 'ad',
            'dev': False
        },
    }, mapu.get_aliases())

  @patch('builtins.open', mock_open(read_data=MULTI_ALIAS_JSON))
  def test_change_map(self):
    mapu = mapuche.mapuche()
    self.assertEqual(None, minqlx_fake.Plugin.current_factory)
    self.assertEqual(None, minqlx_fake.Plugin.current_map_name)
    # force factory
    minqlx_fake.call_command('!mapuche patio ad')
    self.assertEqual('ad', minqlx_fake.Plugin.current_factory)
    self.assertEqual(MULTI_ALIAS_DATA['patio']['mapname'],
                     minqlx_fake.Plugin.current_map_name)
    # default factory
    minqlx_fake.call_command('!mapuche patio')
    self.assertEqual(MULTI_ALIAS_DATA['patio']['factory'],
                     minqlx_fake.Plugin.current_factory)
    self.assertEqual(MULTI_ALIAS_DATA['patio']['mapname'],
                     minqlx_fake.Plugin.current_map_name)
    # dev map
    minqlx_fake.call_command('!mapuche balcon')
    self.assertEqual(MULTI_ALIAS_DATA['balcon']['factory'],
                     minqlx_fake.Plugin.current_factory)
    self.assertEqual(MULTI_ALIAS_DATA['balcon']['mapname'],
                     minqlx_fake.Plugin.current_map_name)

  @patch('builtins.open', mock_open(read_data=MULTI_ALIAS_JSON))
  def test_print_aliases(self):
    mapu = mapuche.mapuche()
    minqlx_fake.call_command('!mapuche_set wasabi duelingkeeps ctf')
    minqlx_fake.call_command('!mapuche_set arriba duelingkeeps ctf')
    minqlx_fake.call_command('!mapuche_aliases')
    clean_log = [l.replace(' ', '') for l in minqlx_fake.Plugin.messages[3:]]
    for alias, data in MULTI_ALIAS_DATA.items():
      dev = '[dev]' if data['dev'] else ''
      self.assertIn(
          '%s:%s(%s)%s' % (alias, data['mapname'], data['factory'], dev),
          clean_log)
    # Check order
    self.assertSequenceEqual(
        sorted(list(MULTI_ALIAS_DATA.keys()) + ['wasabi', 'arriba']),
        [l.split(':')[0] for l in clean_log if ':' in l])


if __name__ == '__main__':
  unittest.main()
