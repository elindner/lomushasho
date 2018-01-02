import sys
import unittest
import minqlx_fake

from unittest.mock import mock_open
from unittest.mock import patch

sys.modules['minqlx'] = minqlx_fake
import mapuche

EMPTY_JSON = '{}\n'
SIMPLE_JSON = '{"playa":"q3wcp16"}'


class TestMapuche(unittest.TestCase):
  def setUp(self):
    minqlx_fake.reset()

  @patch('builtins.open', mock_open(read_data=EMPTY_JSON))
  def test_registers_commands(self):
    mapu = mapuche.mapuche()
    self.assertEqual([
        'mapuche',
        'mapuche_aliases',
        'mapuche_reload',
        'mapuche_remove',
        'mapuche_set'],
        sorted([cmd[0] for cmd in minqlx_fake.registered_commands]))


  @patch('builtins.open', mock_open(read_data=SIMPLE_JSON))
  def test_loads_aliases(self):
    mapu = mapuche.mapuche()
    print(minqlx_fake.last_message)
    self.assertEqual({'playa': 'q3wcp16'}, mapu.get_aliases())


  @patch('builtins.open', mock_open(read_data=SIMPLE_JSON))
  def test_loads_aliases(self):
    mapu = mapuche.mapuche()
    print(minqlx_fake.last_message)
    self.assertEqual({'playa': 'q3wcp16'}, mapu.get_aliases())


if __name__ == '__main__':
    unittest.main()
