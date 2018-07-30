import minqlx_fake
import sys
import unittest

from unittest.mock import mock_open
from unittest.mock import patch
from unittest.mock import MagicMock

sys.modules['minqlx'] = minqlx_fake
import lagparatodos

PLAYER_ID_MAP = {
    10: minqlx_fake.Player(10, ']v[ - cthulhu', ip='1.2.3.4', ping=666),
    11: minqlx_fake.Player(11, '==shub niggurath==', ip='1.2.3.5', ping=10),
    12: minqlx_fake.Player(12, 'Nyarlathotep', ip='1.2.3.6', ping=1000),
    13: minqlx_fake.Player(13, 'Zoth-Ommog', ip='1.2.3.7', ping=0),
}


class TestLagParaTodos(unittest.TestCase):

  def setUp(self):
    minqlx_fake.reset()
    # add ips and pings

  def assertMessages(self, txt):
    self.assertInMessages(txt)
    self.assertEqual(1, len(minqlx_fake.Plugin.messages))

  def assertInMessages(self, txt):
    self.assertTrue(
        [line for line in minqlx_fake.Plugin.messages if txt in line],
        '"%s" not in messages. Messages: %s' % (txt,
                                                minqlx_fake.Plugin.messages))

  def assertSavedConfig(self, expected, mocked_open):
    mocked_open.assert_called_once_with(lagparatodos.CONFIG_FILE_PATH, 'w')
    file_handle = mocked_open.return_value.__enter__.return_value
    if expected:
      first_write = file_handle.writelines.call_args_list[0]
      write_arguments = first_write[0]
      saved_text = write_arguments[0]
      self.assertEqual(sorted(expected), sorted(saved_text))
    else:
      self.assertEqual(0, len(file_handle.writelines.call_args_list))

  def test_registers_commands_and_hooks(self):
    lpt = lagparatodos.lagparatodos()
    self.assertEqual(['lagparatodos'],
                     [cmd[0] for cmd in minqlx_fake.Plugin.registered_commands])

  def test_lagparatodos_no_command(self):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game(PLAYER_ID_MAP, [10, 11], [12, 13], 7, 15)
    minqlx_fake.call_command('!lagparatodos', player)
    self.assertEqual(['Format: !lagparatodos <set|remove>'], player.messages)

  @patch('builtins.open', new_callable=mock_open)
  def test_lagparatodos_set(self, m):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game(PLAYER_ID_MAP, [10, 11], [12, 13], 7, 15)
    minqlx_fake.call_command('!lagparatodos set', player)
    self.assertMessages(
        'LagParaTodos: Rules set. Max ping is 1000ms. Enjoy your lag.')
    self.assertSavedConfig(
        ['1.2.3.4:334', '1.2.3.5:990', '1.2.3.6:0', '1.2.3.7:1000'], m)

  @patch('builtins.open', new_callable=mock_open)
  def test_lagparatodos_reset(self, m):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game(PLAYER_ID_MAP, [10, 11], [12, 13], 7, 15)
    minqlx_fake.call_command('!lagparatodos remove', player)
    self.assertMessages('LagParaTodos: Rules removed. Back to normal.')
    self.assertSavedConfig(None, m)


if __name__ == '__main__':
  unittest.main()
