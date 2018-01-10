import json
import sys
import unittest
import minqlx_fake
import trueskill_fake

from unittest.mock import mock_open
from unittest.mock import patch

sys.modules['minqlx'] = minqlx_fake
sys.modules['trueskill'] = trueskill_fake
import oloraculo

# {type:{id:[mu,sigma,w,l,k,d],...},...}
RATINGS = {
  'ad': {
    123: [25, 1.2, 2, 1, 200, 100],
    456: [30, 1.1, 1, 4, 100, 900],
   },
}
RATINGS_JSON = json.dumps(RATINGS)

GAME_DATA = {
  'TSCORE0': 0,
  'TSCORE1': 8,
  'SCORE_LIMIT': 150,
  'CAPTURE_LIMIT': 8,
  'ABORTED': False,
}

class TestOloraculo(unittest.TestCase):
  def setUp(self):
    minqlx_fake.reset()


  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_registers_commands_and_hooks(self):
    olor = oloraculo.oloraculo()
    self.assertEqual([
        'oloraculo',
        'oloraculo_ratings'],
        sorted([cmd[0] for cmd in minqlx_fake.Plugin.registered_commands]))

    self.assertEqual([
        'game_end',
        'game_start',
        'player_loaded'],
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
      expected_rating = trueskill_fake.Rating(
          expected_player[0], expected_player[1])
      self.assertTrue(
          trueskill_fake.Rating.equals(
              expected_rating, stats.get_rating('ad', player_id)))
      self.assertEqual(
          [expected_player[2], expected_player[3]],
          stats.get_winloss('ad', player_id))
      self.assertEqual(
          [expected_player[4], expected_player[5]],
          stats.get_killdeath('ad', player_id))


  @patch('builtins.open', new_callable=mock_open, read_data=RATINGS_JSON)
  def test_saves_stats(self, m):
    olor = oloraculo.oloraculo()


  @patch('builtins.open', mock_open(read_data=RATINGS_JSON))
  def test_handles_game_end(self):
    olor = oloraculo.oloraculo()
    game_data = {
      'TSCORE0': 7,
      'TSCORE1': 15,
      'SCORE_LIMIT': 15,
      'CAPTURE_LIMIT': 8,
      'ABORTED': False,
    }


  @patch('builtins.open', mock_open(read_data=json.dumps({})))
  def test_handles_player_loaded(self):
    olor = oloraculo.oloraculo()
    self.assertEqual(set(), olor.get_stats().get_player_ids('ad'))
    player = minqlx_fake.Player(123456, 'sarge')
    olor.handle_player_loaded(player)
    self.assertEqual({123456}, olor.get_stats().get_player_ids('ad'))
    self.assertEqual([0, 0], olor.get_stats().get_winloss('ad', 123456))
    self.assertEqual([0, 0], olor.get_stats().get_killdeath('ad', 123456))





if __name__ == '__main__':
    unittest.main()
