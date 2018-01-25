import copy
import datetime
import json
import sys
import unittest
import minqlx_fake

from unittest.mock import mock_open
from unittest.mock import patch

sys.modules['minqlx'] = minqlx_fake
import funes

PLAYER_ID_MAP = {
    12: minqlx_fake.Player(12, 'john'),
    34: minqlx_fake.Player(34, 'paul'),
    56: minqlx_fake.Player(56, 'george'),
    78: minqlx_fake.Player(78, 'ringo'),
    90: minqlx_fake.Player(90, 'cthulhu'),
}

HISTORY_DATA = {
    'ad': {
        '2018-10': {
            '12:34v56:78': [1, 2],
            '12:56v34:78': [1, 20],
            '12:78v34:56': [10, 0],
        },
        '2018-11': {
            '12:34v56:78': [3, 5],
        },
    },
}
HISTORY_JSON = json.dumps(HISTORY_DATA)


class FakeDateWeek10(datetime.date):
  @classmethod
  def today(cls):
    return cls(2018, 3, 6)


class FakeDateWeek4(datetime.date):
  @classmethod
  def today(cls):
    return cls(2018, 1, 24)


class TestFunes(unittest.TestCase):
  def setUp(self):
    minqlx_fake.reset()

  def assertSavedJson(self, expected, mocked_open):
    file_handle = mocked_open.return_value.__enter__.return_value
    first_write = file_handle.write.call_args_list[0]
    write_arguments = first_write[0]
    saved_json = write_arguments[0]
    self.assertEqual(expected, json.loads(saved_json))

  def setup_game_data(
          self,
          red_team_ids,
          blue_team_ids,
          red_score,
          blue_score,
          aborted=False):
    players_by_teams = {'red': [], 'blue': []}
    for player_id in red_team_ids:
      players_by_teams['red'].append(PLAYER_ID_MAP[player_id])
    for player_id in blue_team_ids:
      players_by_teams['blue'].append(PLAYER_ID_MAP[player_id])

    minqlx_fake.Plugin.set_game(minqlx_fake.Game('ad', red_score, blue_score))
    minqlx_fake.Plugin.set_players_by_team(players_by_teams)

    # return the game data obj received by hook handlers.
    return {
        'TSCORE0': red_score,
        'TSCORE1': blue_score,
        'SCORE_LIMIT': 15,
        'CAPTURE_LIMIT': 8,
        'ABORTED': aborted,
    }

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_registers_commands_and_hooks(self):
    fun = funes.funes()
    self.assertEqual(
        ['funes'],
        [cmd[0] for cmd in minqlx_fake.Plugin.registered_commands])

    self.assertEqual(
        ['game_start'],
        [hook[0] for hook in minqlx_fake.Plugin.registered_hooks])

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  def test_loads_history(self):
    fun = funes.funes()
    self.assertEqual(HISTORY_DATA, fun.get_history())

  @patch('builtins.open', mock_open(read_data='invalid'))
  def test_loads_history_invalid_json(self):
    fun = funes.funes()
    self.assertEqual({}, fun.get_history())
    # still usable
    teams = {
        'red': [PLAYER_ID_MAP[id] for id in [34, 12]],
        'blue': [PLAYER_ID_MAP[id] for id in [56, 78]],
    }
    self.assertEqual([0, 0], fun.get_teams_history('ad', teams))
    self.assertEqual([0, 0], fun.get_teams_history('ad', teams, aggregate=True))

  @patch('builtins.open', new_callable=mock_open, read_data=HISTORY_JSON)
  @patch('datetime.date', FakeDateWeek4)
  def test_saves_history_new_date(self, m):
    fun = funes.funes()
    self.assertEqual(HISTORY_DATA, fun.get_history())
    # blue (12 & 34) won
    red_ids = [56, 78]
    blue_ids = [34, 12]
    teams = {
        'red': [PLAYER_ID_MAP[id] for id in red_ids],
        'blue': [PLAYER_ID_MAP[id] for id in blue_ids],
    }
    fun.handle_game_end(self.setup_game_data(red_ids, blue_ids, 7, 15))

    expected = copy.deepcopy(HISTORY_DATA)
    expected['ad']['2018-04'] = {'12:34v56:78': [1, 0]}
    self.assertSavedJson(expected, m)

  @patch('builtins.open', new_callable=mock_open, read_data=HISTORY_JSON)
  @patch('datetime.date', FakeDateWeek10)
  def test_saves_history_same_date(self, m):
    fun = funes.funes()
    self.assertEqual(HISTORY_DATA, fun.get_history())
    # red (34, 56) wins
    red_ids = [56, 34]
    blue_ids = [78, 12]
    teams = {
        'red': [PLAYER_ID_MAP[id] for id in red_ids],
        'blue': [PLAYER_ID_MAP[id] for id in blue_ids],
    }
    fun.handle_game_end(self.setup_game_data(red_ids, blue_ids, 15, 14))

    expected = copy.deepcopy(HISTORY_DATA)
    expected['ad']['2018-10']['12:78v34:56'] = [10, 1]
    self.assertSavedJson(expected, m)

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_get_teams_history(self):
    fun = funes.funes()
    teams = {
        'red': [PLAYER_ID_MAP[id] for id in [34, 12]],
        'blue': [PLAYER_ID_MAP[id] for id in [56, 78]],
    }
    self.assertEqual([1, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([4, 7], fun.get_teams_history('ad', teams, aggregate=True))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_start(self):
    fun = funes.funes()
    game_data = self.setup_game_data([56, 78], [34, 12], 7, 15)
    fun.handle_game_start(game_data)

    def inMes(l, i): return [a for a in l if i in a]

    # session:
    self.assertTrue(
        inMes(minqlx_fake.Plugin.messages, 'george, ringo 2 v 1 john, paul'))
    # historic
    self.assertTrue(
        inMes(minqlx_fake.Plugin.messages, 'george, ringo 7 v 4 john, paul'))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_start_new_player(self):
    fun = funes.funes()
    # id 90 isn't in data
    game_data = self.setup_game_data([56, 78], [34, 90], 7, 15)
    fun.handle_game_start(game_data)

    def inMes(l, i): return [a for a in l if i in a]

    # session:
    self.assertTrue(
        inMes(minqlx_fake.Plugin.messages, 'george, ringo 0 v 0 cthulhu, paul'))
    # historic
    self.assertTrue(
        inMes(minqlx_fake.Plugin.messages, 'george, ringo 0 v 0 cthulhu, paul'))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_end_no_update(self):
    fun = funes.funes()
    red_ids = [56, 78]
    blue_ids = [34, 12]
    teams = {
        'red': [PLAYER_ID_MAP[id] for id in red_ids],
        'blue': [PLAYER_ID_MAP[id] for id in blue_ids],
    }
    self.assertEqual([1, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([4, 7], fun.get_teams_history('ad', teams, aggregate=True))

    # aborted
    fun.handle_game_end(self.setup_game_data(red_ids, blue_ids, 7, 15, True))
    self.assertEqual([1, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([4, 7], fun.get_teams_history('ad', teams, aggregate=True))

    # no team won
    fun.handle_game_end(self.setup_game_data(red_ids, blue_ids, 7, 10))
    self.assertEqual([1, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([4, 7], fun.get_teams_history('ad', teams, aggregate=True))

    # empty team
    fun.handle_game_end(self.setup_game_data([], blue_ids, 7, 15))
    self.assertEqual([1, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([4, 7], fun.get_teams_history('ad', teams, aggregate=True))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_end(self):
    fun = funes.funes()
    red_ids = [56, 78]
    blue_ids = [34, 12]
    teams = {
        'red': [PLAYER_ID_MAP[id] for id in red_ids],
        'blue': [PLAYER_ID_MAP[id] for id in blue_ids],
    }
    self.assertEqual([1, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([4, 7], fun.get_teams_history('ad', teams, aggregate=True))

    # blue (12 & 34) won
    fun.handle_game_end(self.setup_game_data(red_ids, blue_ids, 7, 15))
    self.assertEqual([2, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([5, 7], fun.get_teams_history('ad', teams, aggregate=True))

    # red  (56 & 78) won
    fun.handle_game_end(self.setup_game_data(red_ids, blue_ids, 15, 1))
    self.assertEqual([2, 3], fun.get_teams_history('ad', teams))
    self.assertEqual([5, 8], fun.get_teams_history('ad', teams, aggregate=True))


if __name__ == '__main__':
  unittest.main()
