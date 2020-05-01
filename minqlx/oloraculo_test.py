import json
import re
import sys
import minqlx_fake
import trueskill_fake
import unittest

from unittest.mock import mock_open
from unittest.mock import patch

sys.modules['minqlx'] = minqlx_fake
sys.modules['trueskill'] = trueskill_fake
import oloraculo

# {type:{id:[mu,sigma,w,l,k,d],...},...}
RATINGS = {
    'ad': {
        12: [1, 0, 2, 1, 200, 100],
        34: [2, 0, 1, 4, 100, 900],
        56: [3, 0, 3, 2, 300, 200],
        78: [4, 0, 1, 8, 100, 900],
    },
}
RATINGS_JSON = json.dumps(RATINGS)

PLAYER_ID_MAP = {
    12: minqlx_fake.Player(12, 'john'),
    34: minqlx_fake.Player(34, 'paul'),
    56: minqlx_fake.Player(56, 'george'),
    78: minqlx_fake.Player(78, 'ringo'),
}


class TestOloraculo(unittest.TestCase):

  def setUp(self):
    minqlx_fake.reset()

  def assertSavedJson(self, expected, mocked_open):
    file_handle = mocked_open.return_value.__enter__.return_value
    first_write = file_handle.write.call_args_list[0]
    write_arguments = first_write[0]
    saved_json = write_arguments[0]
    self.assertEqual(expected, json.loads(saved_json))

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_registers_commands_and_hooks(self):
    olor = oloraculo.oloraculo()
    self.assertEqual(
        ['oloraculo', 'oloraculo_stats'],
        sorted([cmd[0] for cmd in minqlx_fake.Plugin.registered_commands]))

    self.assertEqual(
        ['game_end', 'game_start', 'player_loaded'],
        sorted([hook[0] for hook in minqlx_fake.Plugin.registered_hooks]))

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_get_stats_copy(self):
    olor = oloraculo.oloraculo()
    stats = olor.get_stats()
    self.assertEqual(0, len(olor.get_stats().get_player_ids('ad')))
    self.assertEqual(0, len(stats.get_player_ids('ad')))
    stats.new_player('ad', 666)
    self.assertEqual(0, len(olor.get_stats().get_player_ids('ad')))
    self.assertEqual(1, len(stats.get_player_ids('ad')))

  @patch('builtins.open', mock_open(read_data=RATINGS_JSON))
  def test_loads_stats(self):
    olor = oloraculo.oloraculo()
    expected_stats = RATINGS['ad']
    stats = olor.get_stats()
    for player_id in stats.get_player_ids('ad'):
      self.assertTrue(player_id in expected_stats)
      expected_player = expected_stats[player_id]
      expected_rating = trueskill_fake.Rating(expected_player[0],
                                              expected_player[1])
      self.assertEqual(expected_rating, stats.get_rating('ad', player_id))
      self.assertEqual([expected_player[2], expected_player[3]],
                       stats.get_winloss('ad', player_id))
      self.assertEqual([expected_player[4], expected_player[5]],
                       stats.get_killdeath('ad', player_id))

  @patch('builtins.open', mock_open(read_data='invalid'))
  def test_loads_stats_invalid_json(self):
    olor = oloraculo.oloraculo()
    self.assertEqual(set(), olor.get_stats().get_player_ids('ad'))
    # still usable
    minqlx_fake.load_player(minqlx_fake.Player(123456, 'sarge'))
    self.assertEqual({123456}, olor.get_stats().get_player_ids('ad'))

  @patch('builtins.open', new_callable=mock_open, read_data=RATINGS_JSON)
  def test_saves_stats(self, m):
    olor = oloraculo.oloraculo()
    # red_team_ids, blue_team_ids, red_score, blue_score
    minqlx_fake.run_game(PLAYER_ID_MAP, '', [56, 78], [12, 34], 7, 15)
    expected_data = {
        'ad': {
            '12': [2, 0, 3, 1, 200, 100],
            '34': [3, 0, 2, 4, 100, 900],
            '56': [2, 0, 3, 3, 300, 200],
            '78': [3, 0, 1, 9, 100, 900],
        },
    }
    self.assertSavedJson(expected_data, m)

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_handles_player_loaded(self):
    olor = oloraculo.oloraculo()
    self.assertEqual(set(), olor.get_stats().get_player_ids('ad'))
    player = minqlx_fake.Player(123456, 'sarge')
    minqlx_fake.load_player(player)
    self.assertEqual({123456}, olor.get_stats().get_player_ids('ad'))
    self.assertEqual([0, 0], olor.get_stats().get_winloss('ad', 123456))
    self.assertEqual([0, 0], olor.get_stats().get_killdeath('ad', 123456))

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_get_clean_name(self):
    olor = oloraculo.oloraculo()
    self.assertEqual('bluesyquaker', olor.get_clean_name('--bluesyquaker--'))
    self.assertEqual('bluesy quaker', olor.get_clean_name('==bluesy quaker=='))
    self.assertEqual('renga73', olor.get_clean_name(']v[renga73'))
    self.assertEqual('fundiar', olor.get_clean_name(']v[ - fundiar'))
    self.assertEqual('p-lu-k', olor.get_clean_name(']v[ p-lu-k'))
    self.assertEqual('mandiok', olor.get_clean_name('mandiok -- ]v[ --'))
    self.assertEqual('cococrue', olor.get_clean_name('coco]v[crue'))
    self.assertEqual('toro', olor.get_clean_name('toro'))
    self.assertEqual('jaunpi.diazv', olor.get_clean_name('jaunpi.diazv'))
    self.assertEqual('jaunpi', olor.get_clean_name('jaunpi [[KoK]]'))

  @patch('builtins.open', mock_open(read_data=RATINGS_JSON))
  def test_oloraculo_stats(self):
    olor = oloraculo.oloraculo()
    player_names = [PLAYER_ID_MAP[id].name for id in PLAYER_ID_MAP]

    # no players loaded yet
    minqlx_fake.call_command('!oloraculo_stats')
    for player_name in player_names:
      self.assertFalse(player_name in ''.join(minqlx_fake.Plugin.messages))

    minqlx_fake.Plugin.reset_log()

    # players loaded
    for player_id in PLAYER_ID_MAP:
      minqlx_fake.load_player(PLAYER_ID_MAP[player_id])

    minqlx_fake.call_command('!oloraculo_stats')
    for player_name in player_names:
      self.assertTrue(player_name in ''.join(minqlx_fake.Plugin.messages))

  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_oloraculo_stats_no_stats(self):
    olor = oloraculo.oloraculo()
    player_names = [PLAYER_ID_MAP[id].name for id in PLAYER_ID_MAP]

    # no players loaded yet
    minqlx_fake.call_command('!oloraculo_stats')
    for player_name in player_names:
      self.assertFalse(player_name in ''.join(minqlx_fake.Plugin.messages))

    minqlx_fake.Plugin.reset_log()

    # players loaded
    for player_id in PLAYER_ID_MAP:
      minqlx_fake.load_player(PLAYER_ID_MAP[player_id])
    minqlx_fake.call_command('!oloraculo_stats')
    for player_name in player_names:
      self.assertTrue(player_name in ''.join(minqlx_fake.Plugin.messages))

  @patch('builtins.open', mock_open(read_data=RATINGS_JSON))
  def test_handles_game_end(self):
    olor = oloraculo.oloraculo()
    # red_team_ids, blue_team_ids, red_score, blue_score
    minqlx_fake.run_game(PLAYER_ID_MAP, '', [56, 78], [12, 34], 7, 15)
    stats = olor.get_stats()
    # winloss
    self.assertEqual([3, 1], stats.get_winloss('ad', 12))
    self.assertEqual([2, 4], stats.get_winloss('ad', 34))
    self.assertEqual([3, 3], stats.get_winloss('ad', 56))
    self.assertEqual([1, 9], stats.get_winloss('ad', 78))
    # ratings
    self.assertEqual(trueskill_fake.Rating(2), stats.get_rating('ad', 12))
    self.assertEqual(trueskill_fake.Rating(3), stats.get_rating('ad', 34))
    self.assertEqual(trueskill_fake.Rating(2), stats.get_rating('ad', 56))
    self.assertEqual(trueskill_fake.Rating(3), stats.get_rating('ad', 78))

  @patch('builtins.open', mock_open(read_data=RATINGS_JSON))
  def test_handles_game_end_no_update(self):
    olor = oloraculo.oloraculo()
    original_stats = olor.get_stats()

    # aborted
    minqlx_fake.run_game(PLAYER_ID_MAP, '', [56, 78], [12, 34], 7, 15, True)
    self.assertEqual(original_stats, olor.get_stats())

    # final score is < required (15)
    minqlx_fake.run_game(PLAYER_ID_MAP, '', [56, 78], [12, 34], 7, 14)
    self.assertEqual(original_stats, olor.get_stats())

    # all valid
    minqlx_fake.run_game(PLAYER_ID_MAP, '', [56, 78], [12, 34], 7, 16)
    self.assertNotEqual(original_stats, olor.get_stats())

  @patch('builtins.open', mock_open(read_data=RATINGS_JSON))
  def test_oloraculo_no_predictions(self):
    olor = oloraculo.oloraculo()
    # no players loaded
    minqlx_fake.call_command('!oloraculo')
    self.assertFalse(
        [l for l in minqlx_fake.Plugin.messages if 'predictions' in l])

    # only 1 player loaded
    minqlx_fake.Plugin.set_players_by_team({'red': [PLAYER_ID_MAP[12]]})
    minqlx_fake.call_command('!oloraculo')
    self.assertFalse(
        [l for l in minqlx_fake.Plugin.messages if 'predictions' in l])

  @patch('builtins.open', mock_open(read_data=RATINGS_JSON))
  def test_oloraculo(self):

    def match_key(team_a, team_b):
      return repr(sorted((sorted(team_a), sorted(team_b))))

    olor = oloraculo.oloraculo()
    minqlx_fake.Plugin.set_players_by_team({
        'red': [PLAYER_ID_MAP[12], PLAYER_ID_MAP[34]],
        'blue': [PLAYER_ID_MAP[56], PLAYER_ID_MAP[78]]
    })
    minqlx_fake.call_command('!oloraculo')

    expected_predictions = [[1.0000, ['john', 'ringo'], ['paul', 'george']],
                            [0.6667, ['john', 'george'], ['paul', 'ringo']],
                            [0.4286, ['john', 'paul'], ['george', 'ringo']]]

    actual_predictions = [l for l in minqlx_fake.Plugin.messages if ' vs ' in l]
    self.assertEqual(len(expected_predictions), len(actual_predictions))

    for index, expected in enumerate(expected_predictions):
      actual = actual_predictions[index]
      parts = actual.replace(' vs ', ':').replace(' ', '').split(':')
      self.assertEqual(expected[0], float(parts[0]))
      self.assertEqual(match_key(expected[1], expected[2]),
                       match_key(parts[1].split(','), parts[2].split(',')))

  @patch('builtins.open', mock_open(read_data=RATINGS_JSON))
  def test_oloraculo_move_players(self):
    olor = oloraculo.oloraculo()
    minqlx_fake.Plugin.set_players_by_team({
        'red': [
            PLAYER_ID_MAP[12], PLAYER_ID_MAP[34], PLAYER_ID_MAP[56],
            PLAYER_ID_MAP[78]
        ],
        'blue': [],
    })

    # predictions are:
    #   '1.0000 : john, ringo vs paul, george'
    #   '0.6667 : john, george vs paul, ringo'
    #   '0.4286 : john, paul vs george, ringo'
    def teams():
      return [PLAYER_ID_MAP[i].team for i in [12, 34, 56, 78]]

    # invalid, no change
    minqlx_fake.call_command('!oloraculo 0')
    self.assertEqual(['red', 'red', 'red', 'red'], teams())

    minqlx_fake.call_command('!oloraculo 1')
    self.assertEqual(['red', 'blue', 'blue', 'red'], teams())

    minqlx_fake.call_command('!oloraculo 2')
    self.assertEqual(['red', 'blue', 'red', 'blue'], teams())

    minqlx_fake.call_command('!oloraculo 3')
    self.assertEqual(['red', 'red', 'blue', 'blue'], teams())

    # invalid, no change
    minqlx_fake.call_command('!oloraculo 4')
    self.assertEqual(['red', 'red', 'blue', 'blue'], teams())


if __name__ == '__main__':
  unittest.main()
