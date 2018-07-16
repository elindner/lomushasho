import copy
import datetime
import json
import minqlx_fake
import sys
import minqlx_fake
import unittest

from unittest.mock import mock_open
from unittest.mock import patch
from unittest.mock import MagicMock

sys.modules['minqlx'] = minqlx_fake
import timba

PLAYER_ID_MAP = {
    10: minqlx_fake.Player(10, ']v[ - cthulhu'),
    11: minqlx_fake.Player(11, '==shub niggurath=='),
    12: minqlx_fake.Player(12, 'Nyarlathotep'),
    13: minqlx_fake.Player(13, 'Zoth-Ommog'),
}
CREDITS_DATA = {10: 1000, 11: 2000}
CREDITS_JSON = json.dumps(CREDITS_DATA)


def make_bet(team, amount):
  return {'team': team, 'amount': amount}


class TestTimba(unittest.TestCase):

  def setUp(self):
    minqlx_fake.reset()

  def assertInMessages(self, txt):
    self.assertTrue(
        [line for line in minqlx_fake.Plugin.messages if txt in line],
        '"%s" not in messages' % txt)

  def assertSavedJson(self, expected, mocked_open):
    file_handle = mocked_open.return_value.__enter__.return_value
    first_write = file_handle.write.call_args_list[0]
    write_arguments = first_write[0]
    saved_json = write_arguments[0]
    # ugh, needed to make sure all keys are single-quotes strings
    self.assertEqual(json.loads(json.dumps(expected)), json.loads(saved_json))

  def team(self, ids):
    return [PLAYER_ID_MAP[id] for id in ids]

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_registers_commands_and_hooks(self):
    tim = timba.timba()
    self.assertEqual(['timba'],
                     [cmd[0] for cmd in minqlx_fake.Plugin.registered_commands])

    self.assertEqual(['game_countdown', 'game_start', 'game_end'],
                     [hook[0] for hook in minqlx_fake.Plugin.registered_hooks])

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_loads_credits(self):
    tim = timba.timba()
    self.assertEqual(CREDITS_DATA, tim.get_credits())

  @patch('builtins.open', mock_open(read_data='invalid'))
  def test_loads_credits_invalid_json(self):
    tim = timba.timba()
    self.assertEqual({}, tim.get_credits())
    # still usable
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba red 1000', PLAYER_ID_MAP[10])

  @patch('builtins.open', new_callable=mock_open, read_data=CREDITS_JSON)
  def test_saves_credits(self, m):
    tim = timba.timba()
    self.assertEqual(CREDITS_DATA, tim.get_credits())

    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    # blue won
    minqlx_fake.run_game(PLAYER_ID_MAP, [10, 11], [12, 13], 7, 15)

    expected = copy.deepcopy(CREDITS_DATA)
    expected[10] = 2000
    self.assertSavedJson(expected, m)

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_get_credits(self):
    tim = timba.timba()
    self.assertEqual(1000, tim.get_credits()[10])
    self.assertEqual(2000, tim.get_credits()[11])

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_handles_game_countdown(self):
    tim = timba.timba()
    player = PLAYER_ID_MAP[10]
    player.clear_messages()
    self.assertEqual({}, tim.get_current_bets())
    # cannot bet until countdown
    minqlx_fake.call_command('!timba blue 1000', player)
    self.assertEqual({}, tim.get_current_bets())
    self.assertEqual(
        ['You can only bet during warmup. You have 1000 credits to bet.'],
        player.messages)

    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', player)
    self.assertEqual({10: make_bet('blue', 1000)}, tim.get_current_bets())
    minqlx_fake.call_command('!timba red 200', player)
    self.assertEqual({10: make_bet('red', 200)}, tim.get_current_bets())
    minqlx_fake.call_command('!timba red 0', player)
    self.assertEqual({}, tim.get_current_bets())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_handles_game_end(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    new_player = minqlx_fake.Player(666, '*Cthugha*')
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba red 200', PLAYER_ID_MAP[11])
    minqlx_fake.call_command('!timba blue 10', PLAYER_ID_MAP[12])
    minqlx_fake.call_command('!timba red 5000', PLAYER_ID_MAP[13])
    minqlx_fake.call_command('!timba red 4000', new_player)
    # blue won
    minqlx_fake.run_game(PLAYER_ID_MAP, [10, 11], [12, 13], 7, 15)
    self.assertInMessages('cthulhu :  1000 on blue')
    self.assertInMessages('nyarlathotep :    10 on blue')
    self.assertInMessages('shub niggurath :  -200 on red')
    self.assertInMessages('zoth-ommog : -5000 on red')
    self.assertInMessages('cthugha : -4000 on red')

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_handles_game_start(self):
    tim = timba.timba()
    self.assertEqual({}, tim.get_current_bets())
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    self.assertEqual({}, tim.get_current_bets())
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    self.assertEqual({10: make_bet('blue', 1000)}, tim.get_current_bets())
    minqlx_fake.start_game(PLAYER_ID_MAP, [10, 11], [12, 13], 7, 15)
    # should not be allowed
    minqlx_fake.call_command('!timba red 200', PLAYER_ID_MAP[10])
    self.assertEqual({10: make_bet('blue', 1000)}, tim.get_current_bets())
    minqlx_fake.end_game()
    # should not be allowed
    minqlx_fake.call_command('!timba red 200', PLAYER_ID_MAP[10])
    self.assertEqual({}, tim.get_current_bets())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bet_new_player(self):
    tim = timba.timba()
    # id 666 isn't in data
    minqlx_fake.countdown_game()
    new_player = minqlx_fake.Player(666, '*Cthugha*')
    minqlx_fake.call_command('!timba blue 1000', new_player)
    self.assertEqual({666: make_bet('blue', 1000)}, tim.get_current_bets())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bet_invalid_args(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba bblue 1000', PLAYER_ID_MAP[10])
    self.assertEqual({}, tim.get_current_bets())
    minqlx_fake.call_command('!timba blue onemillion', PLAYER_ID_MAP[10])
    self.assertEqual({}, tim.get_current_bets())
    minqlx_fake.call_command('!timba blue one million', PLAYER_ID_MAP[10])
    self.assertEqual({}, tim.get_current_bets())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bet_no_args(self):
    tim = timba.timba()
    player = PLAYER_ID_MAP[10]
    player.clear_messages()
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba', PLAYER_ID_MAP[10])
    self.assertEqual({}, tim.get_current_bets())
    self.assertEqual(['You have 1000 credits to bet.'], player.messages)

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bets_not_enought(self):
    tim = timba.timba()
    player = PLAYER_ID_MAP[10]
    player.clear_messages()
    minqlx_fake.countdown_game()
    # 10 only has 1000 credits
    minqlx_fake.call_command('!timba blue 10000', PLAYER_ID_MAP[10])
    self.assertEqual({}, tim.get_current_bets())
    self.assertEqual(['You only have 1000 credits to bet.'], player.messages)

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bets(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    new_player = minqlx_fake.Player(666, '*Cthugha*')
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba red 200', PLAYER_ID_MAP[11])
    minqlx_fake.call_command('!timba red 4000', new_player)
    # blue won
    minqlx_fake.run_game(PLAYER_ID_MAP, [10, 11], [12, 13], 7, 15)
    self.assertEqual({10: 2000, 11: 1800, 666: 1000}, tim.get_credits())


if __name__ == '__main__':
  unittest.main()
