import copy
import datetime
import json
import minqlx_fake
import sys
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


class FakeTimer(object):

  def __init__(self, delay, function, arguments=None):
    self.delay = delay
    self.function = function
    self.remaining_secs = delay
    self.alive = False

  def start(self):
    self.alive = True
    pass

  def cancel(self):
    self.alive = False
    pass

  def is_alive(self):
    return self.alive

  def tick(self, secs):
    self.remaining_secs -= secs
    if self.remaining_secs < 0:
      self.fire()

  def fire(self):
    self.alive = False
    self.function()


class TestTimba(unittest.TestCase):
  fake_time = 1000

  def setUp(self):
    TestTimba.fake_time = 1000
    self.time_patcher = patch('time.time', lambda: TestTimba.fake_time)
    self.time_patcher.start()
    self.timer_patcher = patch('threading.Timer', FakeTimer)
    self.timer_patcher.start()
    minqlx_fake.reset()

  def tearDown(self):
    self.time_patcher.stop()

  def assertMessages(self, txt):
    self.assertInMessages(txt)
    self.assertEqual(1, len(minqlx_fake.Plugin.messages))

  def assertInMessages(self, txt):
    self.assertTrue(
        [line for line in minqlx_fake.Plugin.messages if txt in line],
        '"%s" not in messages. Messages: %s' %
        (txt, '\n'.join(minqlx_fake.Plugin.messages)))

  def assertSavedJson(self, expected, mocked_open):
    file_handle = mocked_open.return_value.__enter__.return_value
    first_write = file_handle.write.call_args_list[0]
    write_arguments = first_write[0]
    saved_json = write_arguments[0]
    # ugh, needed to make sure all keys are single-quotes strings
    self.assertEqual(json.loads(json.dumps(expected)), json.loads(saved_json))

  def team(self, ids):
    return [PLAYER_ID_MAP[id] for id in ids]

  def run_game(self, tim, red_team_ids, blue_team_ids, red_score, blue_score):
    minqlx_fake.start_game(PLAYER_ID_MAP, '', red_team_ids, blue_team_ids,
                           red_score, blue_score)
    tim.get_betting_timer().fire()
    minqlx_fake.end_game()

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
        ['Betting is not allowed now. You have 1000 credits to bet.'],
        player.messages)
    minqlx_fake.countdown_game()
    self.assertInMessages(
        'Betting is now open: you have 30 seconds to place your bets!')
    minqlx_fake.call_command('!timba blue 1000', player)
    self.assertEqual({10: make_bet('blue', 1000)}, tim.get_current_bets())
    minqlx_fake.call_command('!timba red 200', player)
    self.assertEqual({10: make_bet('red', 200)}, tim.get_current_bets())
    minqlx_fake.call_command('!timba red 0', player)

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_betting_window(self):
    tim = timba.timba()
    player = PLAYER_ID_MAP[10]
    player.clear_messages()
    minqlx_fake.Plugin.set_players_by_team({
        'red': [PLAYER_ID_MAP[13], PLAYER_ID_MAP[11]],
        'blue': [PLAYER_ID_MAP[12], PLAYER_ID_MAP[10]]
    })

    self.assertEqual({}, tim.get_current_bets())
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', player)
    self.assertEqual({10: make_bet('blue', 1000)}, tim.get_current_bets())
    self.assertEqual(('You bet 1000 credits on team blue. ' +
                      'You have 30 seconds to change your bet.'),
                     player.messages.pop())
    # 10 secs passed, we can still bet
    TestTimba.fake_time += 10
    minqlx_fake.call_command('!timba red 1000', player)
    self.assertEqual({10: make_bet('red', 1000)}, tim.get_current_bets())
    self.assertEqual(('You bet 1000 credits on team red. ' +
                      'You have 20 seconds to change your bet.'),
                     player.messages.pop())
    # 29 secs passed, can still bet
    TestTimba.fake_time += 19
    minqlx_fake.call_command('!timba red 100', player)
    self.assertEqual({10: make_bet('red', 100)}, tim.get_current_bets())
    self.assertEqual(('You bet 100 credits on team red. ' +
                      'You have 1 seconds to change your bet.'),
                     player.messages.pop())
    # 30 secs passed, bets closed
    TestTimba.fake_time += 1
    tim.get_betting_timer().fire()
    self.assertInMessages('Betting is now closed. The pot is 100 credits.')
    self.assertEqual(('You bet 100 credits on team red. ' +
                      'You have 900 credits left. Good luck!'),
                     player.messages.pop())
    minqlx_fake.call_command('!timba red 1', player)
    self.assertEqual({10: make_bet('red', 100)}, tim.get_current_bets())
    self.assertEqual('Betting is not allowed now. You have 900 credits to bet.',
                     player.messages.pop())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_no_bets(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    # blue won
    minqlx_fake.Plugin.reset_log()
    self.assertEqual({}, tim.get_current_bets())
    minqlx_fake.start_game(PLAYER_ID_MAP, '', [10, 11], [12, 13], 7, 15)
    tim.get_betting_timer().fire()
    self.assertInMessages('Betting is now closed. There were no bets.')
    self.assertEqual({}, tim.get_current_bets())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_handles_game_start(self):
    tim = timba.timba()
    self.assertEqual({}, tim.get_current_bets())

    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    self.assertEqual({}, tim.get_current_bets())

    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba red 123', PLAYER_ID_MAP[11])
    expected_bets = {10: make_bet('blue', 1000), 11: make_bet('red', 123)}
    self.assertEqual(expected_bets, tim.get_current_bets())
    minqlx_fake.start_game(PLAYER_ID_MAP, '', [10, 11], [12, 13], 7, 15)
    tim.get_betting_timer().fire()
    self.assertInMessages('Betting is now closed. The pot is 1123 credits.')

    # should not be allowed
    minqlx_fake.call_command('!timba red 200', PLAYER_ID_MAP[10])
    self.assertEqual(expected_bets, tim.get_current_bets())
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
  def test_handles_game_end(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    new_player = minqlx_fake.Player(666, '*Cthugha*')
    minqlx_fake.Plugin.players_list.append(new_player)
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba red 200', PLAYER_ID_MAP[11])
    minqlx_fake.call_command('!timba blue 10', PLAYER_ID_MAP[12])
    minqlx_fake.call_command('!timba red 5000', PLAYER_ID_MAP[13])
    minqlx_fake.call_command('!timba red 4000', new_player)
    # blue won
    self.run_game(tim, [10, 11], [12, 13], 7, 15)
    self.assertInMessages('cthulhu :  1000 on blue')
    self.assertInMessages('nyarlathotep :    10 on blue')
    self.assertInMessages('shub niggurath :  -200 on red')
    self.assertInMessages('zoth-ommog : -5000 on red')
    self.assertInMessages('cthugha : -4000 on red')
    self.assertEqual({}, tim.get_current_bets())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_handles_game_aborted_before_start(self):
    tim = timba.timba()
    self.assertEqual({10: 1000, 11: 2000}, tim.get_credits())
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba red 200', PLAYER_ID_MAP[11])
    self.assertEqual({10: 1000, 11: 2000}, tim.get_credits())
    # blue won
    minqlx_fake.start_game(PLAYER_ID_MAP,
                           '', [10, 11], [12, 13],
                           7,
                           15,
                           aborted=True)
    minqlx_fake.end_game()
    self.assertEqual({10: 1000, 11: 2000}, tim.get_credits())
    self.assertEqual({}, tim.get_current_bets())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_handles_game_aborted_after_start(self):
    tim = timba.timba()
    self.assertEqual({10: 1000, 11: 2000}, tim.get_credits())
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba red 200', PLAYER_ID_MAP[11])
    self.assertEqual({10: 1000, 11: 2000}, tim.get_credits())
    # blue won
    minqlx_fake.start_game(PLAYER_ID_MAP,
                           '', [10, 11], [12, 13],
                           7,
                           15,
                           aborted=True)
    tim.get_betting_timer().fire()
    minqlx_fake.end_game()
    self.assertEqual({10: 1000, 11: 2000}, tim.get_credits())
    self.assertEqual({}, tim.get_current_bets())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bets_all_winner(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba red 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba r 200', PLAYER_ID_MAP[11])
    # red won
    self.run_game(tim, [10, 11], [12, 13], 17, 15)
    self.assertEqual({10: 1000, 11: 2000}, tim.get_credits())
    self.assertInMessages(
        'When everyone wins, no one wins: everyone bet on the winner.')
    self.assertEqual({}, tim.get_current_bets())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bets_all_loser(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba red 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba r 200', PLAYER_ID_MAP[11])
    # blue won
    self.run_game(tim, [10, 11], [12, 13], 7, 15)
    self.assertEqual({10: 0, 11: 1800}, tim.get_credits())
    self.assertInMessages('Everyone bet on the loser.')

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bets_one_winner(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    new_player = minqlx_fake.Player(666, '*Cthugha*')
    minqlx_fake.Plugin.players_list.append(new_player)
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba r 200', PLAYER_ID_MAP[11])
    minqlx_fake.call_command('!timba 4000 red', new_player)
    # blue won. pot is 5200
    self.run_game(tim, [10, 11], [12, 13], 7, 15)
    self.assertEqual({10: 5200, 11: 1800, 666: 1000}, tim.get_credits())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bets_multiple_winners(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 100', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba b 25', PLAYER_ID_MAP[11])
    minqlx_fake.call_command('!timba 875 red', PLAYER_ID_MAP[12])

    # blue won. pot is 1000. 10 and 11 won.
    # original credits:
    #   10: 1000
    #   11: 2000
    # winning percentages:
    #   10: 100 / (100 + 25) == 0.8
    #   11: 25 / (100 + 25) == 0.2
    # wins:
    #   10: 1000 * 0.8 == round(800) == 800
    #   12: 1000 * 0.2 == round(200) == 200
    self.run_game(tim, [10, 11], [12, 13], 7, 15)
    self.assertEqual(
        {
            10: 1700,  # original - bet + win == (1000 - 100 + 800)
            11: 2175,  # original - bet + win == (2000 - 25 + 200)
            12: 4125  # original - bet + win == (5000 - 875 + 0)
        },
        tim.get_credits())

  @patch('builtins.open', mock_open(read_data=CREDITS_JSON))
  def test_bets_multiple_winners_rounding(self):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba r 200', PLAYER_ID_MAP[11])
    minqlx_fake.call_command('!timba b 10', PLAYER_ID_MAP[12])
    minqlx_fake.call_command('!timba 4000 red', PLAYER_ID_MAP[13])

    # blue won. pot is 5210. 10 and 12 won.
    # original credits:
    #   10: 1000
    #   12: 5000 (empty)
    # winning percentages:
    #   10: 1000 / (1000 + 10) == 0.99..
    #   12: 10 / (1000 + 10) == 0.0099..
    # wins:
    #   10: 5210 * 0.99.. == round(5158.415841584158) == 5158
    #   12: 5210 * 0.0099.. == round(51.584158415841586) == 52
    self.run_game(tim, [10, 11], [12, 13], 7, 15)
    self.assertEqual(
        {
            10: 5158,  # original - bet + win == (1000 - 1000 + 5158)
            11: 1800,  # original - bet + win == (2000 - 200 + 0)
            12: 5042,  # original - bet + win == (5000 - 10 + 52)
            13: 1000  # original - bet + win == (5000 - 4000 + 0)
        },
        tim.get_credits())

  @patch('builtins.open', new_callable=mock_open, read_data=CREDITS_JSON)
  def test_saves_credits_one_winner(self, m):
    tim = timba.timba()
    self.assertEqual(CREDITS_DATA, tim.get_credits())

    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    # blue won
    self.run_game(tim, [10, 11], [12, 13], 7, 15)

    expected = copy.deepcopy(CREDITS_DATA)
    self.assertSavedJson(expected, m)

  @patch('builtins.open', new_callable=mock_open, read_data=CREDITS_JSON)
  def test_saves_credits_no_winner(self, m):
    tim = timba.timba()
    self.assertEqual(CREDITS_DATA, tim.get_credits())

    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba red 1000', PLAYER_ID_MAP[10])
    # blue won
    self.run_game(tim, [10, 11], [12, 13], 7, 15)

    expected = copy.deepcopy(CREDITS_DATA)
    expected[10] = 0
    self.assertSavedJson(expected, m)

  @patch('builtins.open', new_callable=mock_open, read_data=CREDITS_JSON)
  def test_saves_credits_multiple_winners(self, m):
    tim = timba.timba()
    minqlx_fake.countdown_game()
    minqlx_fake.call_command('!timba blue 1000', PLAYER_ID_MAP[10])
    minqlx_fake.call_command('!timba r 200', PLAYER_ID_MAP[11])
    minqlx_fake.call_command('!timba b 10', PLAYER_ID_MAP[12])
    minqlx_fake.call_command('!timba 4000 red', PLAYER_ID_MAP[13])

    # blue won. pot is 5210. 10 and 12 won.
    # original credits:
    #   10: 1000
    #   12: 5000 (empty)
    # winning percentages:
    #   10: 1000 / (1000 + 10) == 0.99..
    #   12: 10 / (1000 + 10) == 0.0099..
    # wins:
    #   10: 5210 * 0.99.. == round(5158.415841584158) == 5158
    #   12: 5210 * 0.0099.. == round(51.584158415841586) == 52
    self.run_game(tim, [10, 11], [12, 13], 7, 15)

    self.assertEqual(
        {
            10: 5158,  # original - bet + win == (1000 - 1000 + 5158)
            11: 1800,  # original - bet + win == (2000 - 200 + 0)
            12: 5042,  # original - bet + win == (5000 - 10 + 52)
            13: 1000  # original - bet + win == (5000 - 4000 + 0)
        },
        tim.get_credits())

    expected = {'10': 5158, '11': 1800, '12': 5042, '13': 1000}
    self.assertSavedJson(expected, m)


if __name__ == '__main__':
  unittest.main()
