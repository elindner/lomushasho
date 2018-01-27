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
    10: minqlx_fake.Player(10, 'mandiok'),
    11: minqlx_fake.Player(11, 'fundi'),
    12: minqlx_fake.Player(12, 'toro'),
    13: minqlx_fake.Player(13, 'peluca'),
    14: minqlx_fake.Player(14, 'renga'),
    15: minqlx_fake.Player(15, 'coco'),
    16: minqlx_fake.Player(16, 'blues'),
    17: minqlx_fake.Player(17, 'juanpi'),
    90: minqlx_fake.Player(90, 'cthulhu'),
}

HISTORY_DATA = [
    ['2018-10', 'ad', [10, 11, 12], [13, 14, 15], 17, 16],
    ['2018-10', 'ad', [11, 13, 14], [10, 12, 15], 15, 8],
    ['2018-10', 'ad', [10, 12, 15], [11, 13, 14], 15, 8],
    ['2018-10', 'ad', [10, 12, 15], [11, 13, 14], 15, 12],
    ['2018-10', 'ad', [11, 14, 15], [10, 12, 13], 16, 8],
    ['2018-10', 'ad', [10, 12, 13], [11, 14, 15], 16, 7],

    ['2018-11', 'ad', [13, 14, 16], [10, 12, 15], 16, 14],
    ['2018-11', 'ad', [11, 13, 14], [12, 15, 16], 15, 11],
    ['2018-11', 'ad', [10, 12, 15], [11, 13, 14], 17, 8],
    ['2018-11', 'ad', [10, 11, 12], [13, 14, 15], 15, 12],
    ['2018-11', 'ad', [13, 14, 15], [10, 11, 12], 16, 13],
    ['2018-11', 'ad', [10, 11, 12], [13, 14, 15], 21, 20],
    ['2018-11', 'ad', [13, 14, 15], [10, 11, 12], 15, 2],

    ['2018-12', 'ad', [10, 15], [11, 13], 16, 11],
    ['2018-12', 'ad', [10, 13, 14], [11, 15, 16], 17, 12],
    ['2018-12', 'ad', [11, 14, 15, 17], [10, 12, 13, 16], 15, 2],
    ['2018-12', 'ad', [10, 13, 15, 16], [11, 12, 14, 17], 16, 11],
    ['2018-12', 'ad', [10, 13, 15, 16], [11, 12, 14, 17], 16, 9],
    ['2018-12', 'ad', [10, 12, 14], [13, 15, 16], 16, 3],
    ['2018-12', 'ad', [10, 13, 16], [12, 14, 15], 17, 6],
    ['2018-12', 'ad', [13, 14, 15], [10, 12, 16], 17, 7],
    ['2018-12', 'ad', [13, 14, 15], [10, 12, 16], 18, 16],
    ['2018-12', 'ctf', [15, 16], [10, 12], 8, 3],

    ['2018-13', 'ad', [10, 12, 14], [11, 13, 16], 15, 5],
    ['2018-13', 'ad', [10, 12, 14], [11, 13, 16], 15, 0],
    ['2018-13', 'ad', [11, 14, 15], [10, 13, 16], 16, 14],
    ['2018-13', 'ad', [10, 13, 16], [11, 14, 15], 17, 16],
    ['2018-13', 'ad', [10, 13, 16], [12, 14, 15], 15, 5],
    ['2018-13', 'ad', [13, 14, 15], [10, 12, 16], 15, 4],
    ['2018-13', 'ad', [10, 11, 12], [13, 14, 15], 17, 15],
    ['2018-13', 'ad', [10, 11, 12], [13, 14, 15], 17, 12],
    ['2018-13', 'ad', [11, 13, 15], [10, 12, 14], 15, 7],
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
        ['game_start', 'game_end'],
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
    # blue won
    red_ids = [15, 12]
    blue_ids = [13, 16]
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 7, 15)
    minqlx_fake.end_game()

    expected = copy.deepcopy(HISTORY_DATA)
    expected.append(['2018-04', 'ad', [12, 15], [13, 16], 7, 15])
    self.assertSavedJson(expected, m)

  @patch('builtins.open', new_callable=mock_open, read_data=HISTORY_JSON)
  @patch('datetime.date', FakeDateWeek10)
  def test_saves_history_same_date(self, m):
    fun = funes.funes()
    self.assertEqual(HISTORY_DATA, fun.get_history())
    red_ids = [15, 12]
    blue_ids = [13, 16]
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 15, 14)
    minqlx_fake.end_game()

    expected = copy.deepcopy(HISTORY_DATA)
    expected.append(['2018-10', 'ad', [12, 15], [13, 16], 15, 14])
    self.assertSavedJson(expected, m)

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_get_teams_history(self):
    fun = funes.funes()
    teams = ((10, 11, 12), (15, 13, 14))
    self.assertEqual([1, 0], fun.get_teams_history('ad', teams))
    self.assertEqual([5, 2], fun.get_teams_history('ad', teams, aggregate=True))

    # change order
    teams = ((15, 13, 14), (10, 11, 12))
    self.assertEqual([0, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([2, 5], fun.get_teams_history('ad', teams, aggregate=True))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_start(self):
    fun = funes.funes()
    test_util.setup_game_data(PLAYER_ID_MAP, [11, 13, 14], [12, 10, 15], 7, 15)
    minqlx_fake.start_game()

    # session, historic
    self.assertInMessages('fundi, peluca, renga 1 v 2 coco, mandiok, toro')
    self.assertInMessages('                     1 v 3 (since 2018w10)')

    # flip red and blue teams:
    minqlx_fake.Plugin.reset_log()
    test_util.setup_game_data(PLAYER_ID_MAP, [12, 10, 15], [11, 13, 14], 15, 1)
    minqlx_fake.start_game()

    msgs = minqlx_fake.Plugin.messages
    # session, historic
    self.assertInMessages('coco, mandiok, toro 2 v 1 fundi, peluca, renga')
    self.assertInMessages('                    3 v 1 (since 2018w10)')

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_start_new_player(self):
    fun = funes.funes()
    # id 90 isn't in data
    test_util.setup_game_data(PLAYER_ID_MAP, [11, 13, 14], [12, 10, 90], 7, 15)
    # test_util.setup_game_data(PLAYER_ID_MAP, [56, 78], [34, 90], 7, 15)
    minqlx_fake.start_game()

    msgs = minqlx_fake.Plugin.messages
    # session, historic
    self.assertInMessages('fundi, peluca, renga 0 v 0 cthulhu, mandiok, toro')
    self.assertInMessages('fundi, peluca, renga 0 v 0 cthulhu, mandiok, toro')

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_end_no_update(self):
    fun = funes.funes()
    red_ids = [10, 15, 12]
    blue_ids = [11, 14, 13]
    teams = (red_ids, blue_ids)
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 1], fun.get_teams_history('ad', teams, aggregate=True))

    # aborted
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 7, 15, True)
    minqlx_fake.end_game()
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 1], fun.get_teams_history('ad', teams, aggregate=True))

    # no team won
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 7, 10)
    minqlx_fake.end_game()
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 1], fun.get_teams_history('ad', teams, aggregate=True))

    # empty team
    test_util.setup_game_data(PLAYER_ID_MAP, [], blue_ids, 7, 15)
    minqlx_fake.end_game()
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([3, 1], fun.get_teams_history('ad', teams, aggregate=True))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_handles_game_end(self):
    fun = funes.funes()
    red_ids = [10, 11, 12]
    blue_ids = [15, 13, 14]
    teams = (red_ids, blue_ids)
    self.assertEqual([1, 0], fun.get_teams_history('ad', teams))
    self.assertEqual([5, 2], fun.get_teams_history('ad', teams, aggregate=True))

    # blue won
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 7, 15)
    minqlx_fake.end_game()
    self.assertEqual([1, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([5, 3], fun.get_teams_history('ad', teams, aggregate=True))

    # red won
    test_util.setup_game_data(PLAYER_ID_MAP, red_ids, blue_ids, 15, 1)
    minqlx_fake.end_game()
    self.assertEqual([2, 1], fun.get_teams_history('ad', teams))
    self.assertEqual([6, 3], fun.get_teams_history('ad', teams, aggregate=True))

  @patch('builtins.open', mock_open(read_data=HISTORY_JSON))
  @patch('datetime.date', FakeDateWeek10)
  def test_funes(self):
    fun = funes.funes()
    player_names = [PLAYER_ID_MAP[id].name for id in PLAYER_ID_MAP]

    # no players loaded yet
    minqlx_fake.call_command('!funes')
    for player_name in player_names:
      self.assertNotInMessages(player_name)

    # no matches today and no history
    minqlx_fake.Plugin.reset_log()
    minqlx_fake.Plugin.set_players_by_team({
        'red': [PLAYER_ID_MAP[13], PLAYER_ID_MAP[16]],
        'blue': [PLAYER_ID_MAP[12], PLAYER_ID_MAP[10]]
    })
    minqlx_fake.call_command('!funes')
    self.assertInMessages('Since 2018w10: no history with these players.')
    self.assertInMessages('Today: no history with these players.')

    # no matches today, some history
    minqlx_fake.Plugin.reset_log()
    minqlx_fake.Plugin.set_players_by_team({
        'red': [PLAYER_ID_MAP[13], PLAYER_ID_MAP[16], PLAYER_ID_MAP[15]],
        'blue': [PLAYER_ID_MAP[12], PLAYER_ID_MAP[10], PLAYER_ID_MAP[14]]
    })
    minqlx_fake.call_command('!funes')
    msgs = minqlx_fake.Plugin.messages
    self.assertInMessages('mandiok, toro, blues  0  v  3  peluca, renga, coco')
    self.assertInMessages('mandiok, peluca, blues  2  v  0  toro, renga, coco')
    self.assertInMessages('mandiok, toro, renga  1  v  0  peluca, coco, blues')
    self.assertInMessages('mandiok, toro, coco  0  v  1  peluca, renga, blues')
    self.assertInMessages('Today: no history with these players.')

    # both matches today and history
    minqlx_fake.Plugin.reset_log()
    minqlx_fake.Plugin.set_players_by_team({
        'red': [PLAYER_ID_MAP[10], PLAYER_ID_MAP[11], PLAYER_ID_MAP[12]],
        'blue': [PLAYER_ID_MAP[13], PLAYER_ID_MAP[14], PLAYER_ID_MAP[15]]
    })
    minqlx_fake.call_command('!funes')
    msgs = minqlx_fake.Plugin.messages
    self.assertInMessages('mandiok, toro, coco  2  v  1  fundi, peluca, renga')
    self.assertInMessages('mandiok, toro, peluca  1  v  1  fundi, renga, coco')
    self.assertInMessages('mandiok, fundi, toro  1  v  0  peluca, renga, coco')
    self.assertInMessages('mandiok, fundi, toro  5  v  2  peluca, renga, coco')
    self.assertInMessages('mandiok, toro, coco  3  v  1  fundi, peluca, renga')
    self.assertInMessages('mandiok, toro, peluca  1  v  1  fundi, renga, coco')
    self.assertInMessages('mandiok, toro, renga  0  v  1  fundi, peluca, coco')


if __name__ == '__main__':
  unittest.main()
