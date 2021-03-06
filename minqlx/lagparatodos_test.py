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

  def assertMessages(self, expected):
    expected_string = '\n'.join([l for l in expected if l])
    actual_string = '\n'.join([l for l in minqlx_fake.Plugin.messages if l])
    self.assertIn(expected_string, actual_string)

  def assertSavedConfig(self, expected, mocked_open):
    mocked_open.assert_called_once_with(lagparatodos.CONFIG_FILE_PATH, 'w')
    file_handle = mocked_open.return_value.__enter__.return_value
    if expected:
      first_write = file_handle.writelines.call_args_list[0]
      write_arguments = first_write[0]
      saved_text = write_arguments[0]
      self.assertEqual(sorted(['%s\n' % l for l in expected]),
                       sorted(saved_text))
    else:
      self.assertEqual(0, len(file_handle.writelines.call_args_list))

  def test_registers_commands_and_hooks(self):
    lpt = lagparatodos.lagparatodos()
    self.assertEqual(['lagparatodos'],
                     [cmd[0] for cmd in minqlx_fake.Plugin.registered_commands])

  def test_parse_params(self):
    lpt = lagparatodos.lagparatodos()

    def assertParams(command, whitelist, latency_limit, command_line):
      args = [None] + command_line.split(' ')
      actual = lpt.parse_params(args)
      self.assertEqual(command, actual['command'])
      self.assertEqual(whitelist, actual['whitelist'])
      self.assertEqual(latency_limit, actual['latency_limit'])

    self.assertEqual(None, lpt.parse_params(''))
    self.assertEqual(None, lpt.parse_params('something'))

    assertParams('remove', [], None, 'remove')
    assertParams('remove', [], None, 'remove something')

    assertParams('set', [], None, 'set')
    assertParams('set', [], None, 'set something')
    assertParams('set', [], 100, 'set 100')
    assertParams('set', ['1.2.3.4'], None, 'set 1.2.3.4')
    assertParams('set', ['1.2.3.4', '5.6.7.8'], None, 'set 1.2.3.4,5.6.7.8')
    assertParams('set', ['1.2.3.4', '5.6.7.8'], None, 'set 1.2.3.4,5.6.7.8,!!')

    assertParams('set', ['1.2.3.4'], 666, 'set 1.2.3.4 666')
    assertParams('set', ['1.2.3.4'], 666, 'set 666 1.2.3.4')
    assertParams('set', ['1.2.3.4', '5.6.7.8'], 123, 'set 123 1.2.3.4,5.6.7.8')
    assertParams('set', ['1.2.3.4', '5.6.7.8'], 123,
                 'set 1.2.3.4,5.6.7.8,!! 123')

  def test_lagparatodos_no_command(self):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game(PLAYER_ID_MAP, '', [10, 11], [12, 13], 7, 15)
    minqlx_fake.call_command('!lagparatodos', player)
    self.assertEqual(
        ['Format: !lagparatodos <set|remove> [whitelist] [latency_limit]'],
        player.messages)

  @patch('builtins.open', new_callable=mock_open)
  def test_lagparatodos_reset(self, m):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game(PLAYER_ID_MAP, '', [10, 11], [12, 13], 7, 15)
    minqlx_fake.call_command('!lagparatodos remove', player)
    self.assertMessages(['LagParaTodos: Rules removed. Back to normal.'])
    self.assertSavedConfig(None, m)

  @patch('builtins.open', new_callable=mock_open)
  def test_lagparatodos_set(self, m):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game(PLAYER_ID_MAP, '', [10, 11], [12, 13], 7, 15)
    minqlx_fake.call_command('!lagparatodos set', player)
    self.assertMessages([
        '          zoth-ommog: 1000ms added',
        '      shub niggurath:  990ms added',
        '             cthulhu:  334ms added',
        '        nyarlathotep: ------ over limit',
        'Rules set. Enjoy your lag! >:[',
    ])
    self.assertSavedConfig(
        ['1.2.3.4:334', '1.2.3.5:990', '1.2.3.6:0', '1.2.3.7:1000'], m)

  @patch('builtins.open', new_callable=mock_open)
  def test_lagparatodos_set_only_one_player(self, m):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game({10: PLAYER_ID_MAP[10]}, '', [10], [], 7, 15)
    minqlx_fake.call_command('!lagparatodos set', player)
    self.assertMessages(
        ['There should be at least two players. Nothing changed'])

  @patch('builtins.open', new_callable=mock_open)
  def test_lagparatodos_set_latency_limit(self, m):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game(PLAYER_ID_MAP, '', [10, 11], [12, 13], 7, 15)
    minqlx_fake.call_command('!lagparatodos set 500', player)
    self.assertMessages([
        '          zoth-ommog:  500ms added',
        '      shub niggurath:  490ms added',
        '             cthulhu: ------ over limit',
        '        nyarlathotep: ------ over limit',
        'Rules set. Enjoy your lag! >:[',
    ])
    self.assertSavedConfig(
        ['1.2.3.4:0', '1.2.3.5:490', '1.2.3.6:0', '1.2.3.7:500'], m)

  @patch('builtins.open', new_callable=mock_open)
  def test_lagparatodos_set_whitelist(self, m):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game(PLAYER_ID_MAP, '', [10, 11], [12, 13], 7, 15)
    minqlx_fake.call_command('!lagparatodos set 1.2.3.5', player)
    self.assertMessages([
        '          zoth-ommog: 1000ms added',
        '             cthulhu:  334ms added',
        '      shub niggurath: ------ whitelisted',
        '        nyarlathotep: ------ over limit',
        'Rules set. Enjoy your lag! >:[',
    ])
    self.assertSavedConfig(
        ['1.2.3.4:334', '1.2.3.5:0', '1.2.3.6:0', '1.2.3.7:1000'], m)

    m.reset_mock()
    minqlx_fake.call_command('!lagparatodos set 1.2.3.6,1.2.3.7', player)
    self.assertMessages([
        '      shub niggurath:  656ms added',
        '        nyarlathotep: ------ whitelisted',
        '          zoth-ommog: ------ whitelisted',
        '             cthulhu: ------ over limit',
        'Rules set. Enjoy your lag! >:[',
    ])
    self.assertSavedConfig(
        ['1.2.3.4:0', '1.2.3.5:656', '1.2.3.6:0', '1.2.3.7:0'], m)

  @patch('builtins.open', new_callable=mock_open)
  def test_lagparatodos_set_whitelist_and_latency_limit(self, m):
    lpt = lagparatodos.lagparatodos()
    player = PLAYER_ID_MAP[10]
    minqlx_fake.start_game(PLAYER_ID_MAP, '', [10, 11], [12, 13], 7, 15)
    minqlx_fake.call_command('!lagparatodos set 1.2.3.5 500', player)
    self.assertMessages([
        '          zoth-ommog:  500ms added',
        '      shub niggurath: ------ whitelisted',
        '             cthulhu: ------ over limit',
        '        nyarlathotep: ------ over limit',
        'Rules set. Enjoy your lag! >:[',
    ])
    self.assertSavedConfig(
        ['1.2.3.4:0', '1.2.3.5:0', '1.2.3.6:0', '1.2.3.7:500'], m)

    m.reset_mock()
    minqlx_fake.call_command('!lagparatodos set 5 1.2.3.6,1.2.3.7', player)
    self.assertMessages([
        '        nyarlathotep: ------ whitelisted',
        '          zoth-ommog: ------ whitelisted',
        '      shub niggurath: ------ over limit',
        '             cthulhu: ------ over limit',
        'Rules set. Enjoy your lag! >:[',
    ])
    self.assertSavedConfig(['1.2.3.4:0', '1.2.3.5:0', '1.2.3.6:0', '1.2.3.7:0'],
                           m)


if __name__ == '__main__':
  unittest.main()
