import copy
import datetime
import json
import minqlx_fake
import sys
import test_util
import unittest

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

HISTORY_DATA_BIG = [
    ['2018-01', 'ad', [10, 11, 12], [13, 15, 14], 17, 16],
    ['2018-01', 'ad', [11, 13, 14], [15, 10, 12], 15, 8],
    ['2018-01', 'ad', [10, 15, 12], [14, 11, 13], 15, 8],
    ['2018-01', 'ad', [10, 15, 12], [11, 14, 13], 15, 12],
    ['2018-01', 'ad', [15, 14, 11], [10, 13, 12], 16, 8],
    ['2018-01', 'ad', [10, 12, 13], [15, 11, 14], 16, 7],
    ['2018-02', 'ad', [13, 16, 14], [15, 10, 12], 16, 14],
    ['2018-02', 'ad', [13, 11, 14], [15, 16, 12], 15, 11],
    ['2018-02', 'ad', [10, 15, 12], [11, 13, 14], 17, 8],
    ['2018-02', 'ad', [10, 11, 12], [15, 13, 14], 15, 12],
    ['2018-02', 'ad', [15, 13, 14], [10, 11, 12], 16, 13],
    ['2018-02', 'ad', [10, 11, 12], [13, 15, 14], 21, 20],
    ['2018-02', 'ad', [15, 13, 14], [10, 11, 12], 15, 2],
    ['2018-03', 'ad', [15, 10], [13, 11], 16, 11],
    ['2018-03', 'ad', [10, 13, 14], [15, 16, 11], 17, 12],
    ['2018-03', 'ad', [15, 17, 14, 11], [16, 10, 13, 12], 15, 2],
    ['2018-03', 'ad', [15, 10, 16, 13], [17, 11, 14, 12], 16, 11],
    ['2018-03', 'ad', [13, 15, 10, 16], [17, 14, 12, 11], 16, 9],
    ['2018-03', 'ad', [10, 14, 12], [15, 16, 13], 16, 3],
    ['2018-03', 'ad', [10, 13, 16], [15, 12, 14], 17, 6],
    ['2018-03', 'ad', [13, 15, 14], [10, 16, 12], 17, 7],
    ['2018-03', 'ad', [15, 14, 13], [10, 12, 16], 18, 16],
    ['2018-03', 'ctf', [16, 15], [10, 12], 8, 3],
]

HISTORY_DATA = [
    # 2018-10
    # 56,78 [ 2 v 1 ] 12,34
    ['2018-10', 'ad', [12, 34], [56, 78], 15, 0],
    ['2018-10', 'ad', [12, 34], [56, 78], 11, 15],
    ['2018-10', 'ad', [56, 78], [12, 34], 15, 5],
    # 34,78 [ 2 v 0 ] 12,56
    ['2018-10', 'ad', [34, 78], [12, 56], 15, 5],
    ['2018-10', 'ad', [12, 56], [78, 34], 0, 15],
    # 2018-11
    # 12,34 [ 1 v 1 ] 56,78
    ['2018-11', 'ad', [12, 34], [56, 78], 15, 0],
    ['2018-11', 'ad', [12, 34], [56, 78], 1, 15],
]

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

  def assertInMessages(self, txt):
    self.assertTrue(
        [line for line in minqlx_fake.Plugin.messages if txt in line])

  def assertNotInMessages(self, txt):
    self.assertFalse(
        [line for line in minqlx_fake.Plugin.messages if txt in line])

  def assertSavedJson(self, expected, mocked_open):
    file_handle = mocked_open.return_value.__enter__.return_value
    first_write = file_handle.write.call_args_list[0]
    write_arguments = first_write[0]
    saved_json = write_arguments[0]
    self.assertEqual(expected, json.loads(saved_json))

  def team(self, ids):
    return [PLAYER_ID_MAP[id] for id in ids]

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_registers_commands_and_hooks(self):
    fun = funes.funes()
    self.assertEqual(
        ['funes'],
        [cmd[0] for cmd in minqlx_fake.Plugin.registered_commands])

    self.assertEqual(
        ['game_start', 'game_end', 'player_loaded'],
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
    teams = ((34, 12), (56, 78))
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
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 7, 15)
    minqlx_fake.end_game()

    expected = copy.deepcopy(HISTORY_DATA)
    expected.append(['2018-04', 'ad', [56, 78], [12, 34], 7, 15])
    self.assertSavedJson(expected, m)

  @patch('builtins.open', new_callable=mock_open, read_data=HISTORY_JSON)
  @patch('datetime.date', FakeDateWeek10)
  def test_saves_history_same_date(self, m):
    fun = funes.funes()
    self.assertEqual(HISTORY_DATA, fun.get_history())
    # (34, 56) wins
    red_ids = [56, 34]
    blue_ids = [78, 12]
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 15, 14)
    minqlx_fake.end_game()

    expected = copy.deepcopy(HISTORY_DATA)
    expected.append(['2018-10', 'ad', [34, 56], [12, 78], 15, 14])
    self.assertSavedJson(expected, m)

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_get_teams_history(self):
    fun = funes.funes()
    teams = ((34, 12), (56, 78))
    self.assertEqual([1, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([2, 3], fun.get_teams_history('ad', teams, aggregate=True))

    # change order
    teams = ((78, 56), (12, 34))
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 2], fun.get_teams_history('ad', teams, aggregate=True))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_start(self):
    fun = funes.funes()
    test_util.setup_game_data(PLAYER_ID_MAP, [56, 78], [34, 12], 7, 15)
    minqlx_fake.start_game()

    # session:
    self.assertInMessages('george, ringo 2 v 1 john, paul')
    # historic
    self.assertInMessages('george, ringo 3 v 2 john, paul')

    # flip red and blue teams:
    minqlx_fake.Plugin.reset_log()
    test_util.setup_game_data(PLAYER_ID_MAP, [12, 34], [78, 56], 15, 1)
    minqlx_fake.start_game()

    msgs = minqlx_fake.Plugin.messages
    # session:
    self.assertInMessages('john, paul 1 v 2 george, ringo')
    # historic
    self.assertInMessages('john, paul 2 v 3 george, ringo')

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_start_new_player(self):
    fun = funes.funes()
    # id 90 isn't in data
    test_util.setup_game_data(PLAYER_ID_MAP, [56, 78], [34, 90], 7, 15)
    minqlx_fake.start_game()

    msgs = minqlx_fake.Plugin.messages
    # session:
    self.assertInMessages('george, ringo 0 v 0 cthulhu, paul')
    # historic
    self.assertInMessages('george, ringo 0 v 0 cthulhu, paul')

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_end_no_update(self):
    fun = funes.funes()
    red_ids = [56, 78]
    blue_ids = [34, 12]
    teams = (red_ids, blue_ids)
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 2], fun.get_teams_history('ad', teams, aggregate=True))

    # aborted
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 7, 15, True)
    minqlx_fake.end_game()
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 2], fun.get_teams_history('ad', teams, aggregate=True))

    # no team won
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 7, 10)
    minqlx_fake.end_game()
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 2], fun.get_teams_history('ad', teams, aggregate=True))

    # empty team
    test_util.setup_game_data(PLAYER_ID_MAP, [], blue_ids, 7, 15)
    minqlx_fake.end_game()
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 2], fun.get_teams_history('ad', teams, aggregate=True))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_end(self):
    fun = funes.funes()
    red_ids = [56, 78]
    blue_ids = [34, 12]
    teams = (red_ids, blue_ids)
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 2], fun.get_teams_history('ad', teams, aggregate=True))

    # blue (12 & 34) won
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 7, 15)
    minqlx_fake.end_game()
    self.assertEqual([2, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 3], fun.get_teams_history('ad', teams, aggregate=True))

    # red  (56 & 78) won
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 15, 1)
    minqlx_fake.end_game()
    self.assertEqual([3, 2], fun.get_teams_history('ad', teams))
    self.assertEqual([4, 3], fun.get_teams_history('ad', teams, aggregate=True))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_funes(self):
    fun = funes.funes()
    player_names = [PLAYER_ID_MAP[id].name for id in PLAYER_ID_MAP]

    # no players loaded yet
    minqlx_fake.call_command('!funes')

    for player_name in player_names:
      self.assertNotInMessages(player_name)

    # with players
    minqlx_fake.Plugin.reset_log()
    minqlx_fake.Plugin.set_players_by_team({
        'red': [PLAYER_ID_MAP[12], PLAYER_ID_MAP[34]],
        'blue': [PLAYER_ID_MAP[56], PLAYER_ID_MAP[78]]
    })
    minqlx_fake.call_command('!funes')

    msgs = minqlx_fake.Plugin.messages
    self.assertInMessages('john, paul  1  v  2  george, ringo')
    self.assertInMessages('john, george  0  v  1  paul, ringo')
    self.assertInMessages('john, ringo  0  v  0  paul, george')
    # historicals
    self.assertInMessages('john, paul  2  v  3  george, ringo')
    self.assertInMessages('john, george  0  v  1  paul, ringo')
    self.assertInMessages('john, ringo  0  v  0  paul, george')


if __name__ == '__main__':
  unittest.main()
