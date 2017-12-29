import itertools
import json
import minqlx
import os
import re
import trueskill


"""
Steam Ids, for reference
76561197969594389 - goras
76561198014448247 - blues
76561198015775820 - renga
76561198045070268 - fundi
76561198257667410 - cfer
76561198257902041 - mandiok
76561198261371023 - coco
76561198282206581 - toro
76561198280762419 - juanpi
"""

"""
JSON data file for reference:
{
  "game_type": {
    "steam_id": [rating_mu, rating_sigma, games_won, games_lost],
    ...
  },
  ...
}
"""

TESTING = False

PRESENT_TEST = [
  76561198014448247,
  76561198015775820,
  76561198045070268,
  76561198257902041,
  76561198261371023,
  76561198282206581,
  76561198280762419
]

PLAYER_ID_MAP_TEST = {
  76561198014448247: '--bluesyquaker--',
  76561198015775820: ']v[renga73',
  76561198045070268: ']v[ - fundiar',
  76561198257667410: ']v[ p-lu-k',
  76561198257902041: 'mandiok -- ]v[ --',
  76561198261371023: 'coco]v[crue',
  76561198282206581: 'toro',
  76561198280762419: 'jaunpi.diazv'
}


HEADER_COLOR_STRING = '^2'
if TESTING:
  JSON_FILE_NAME = 'oloraculo_stats.json.testing'
else:
  JSON_FILE_NAME = 'oloraculo_stats.json'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_FILE_PATH = os.path.join(ROOT_PATH, JSON_FILE_NAME)
INTERESTING_GAME_TYPES = ['ad', 'ctf']


class Db(object):
  def __init__(self):
    # {'game_type': {'player_id': trueskill.Rating, ...}, ...}
    self._ratings_dict = {}

    # {'game_type': {'player_id': [win, loss], ...}, ...}
    self._winloss_dict = {}

    # {'game_type': {'player_id': [kill, death], ...}, ...}
    self._killdeath_dict = {}


  def _ratings(self, game_type):
    return self._ratings_dict.setdefault(game_type, {})


  def _winloss(self, game_type):
    return self._winloss_dict.setdefault(game_type, {})


  def _killdeath(self, game_type):
    return self._killdeath_dict.setdefault(game_type, {})


  def set_rating(self, game_type, player_id, rating):
    self._ratings(game_type)[int(player_id)] = rating


  def set_winloss(self, game_type, player_id, winloss):
    self._winloss(game_type)[int(player_id)] = list(winloss)


  def set_killdeath(self, game_type, player_id, killdeath):
    self._killdeath(game_type)[int(player_id)] = list(killdeath)


  def get_rating(self, game_type, player_id):
    return self._ratings(game_type).setdefault(
        int(player_id), trueskill.Rating())


  def get_winloss(self, game_type, player_id):
    return self._winloss(game_type).setdefault(int(player_id), [0, 0])


  def get_killdeath(self, game_type, player_id):
    return self._killdeath(game_type).setdefault(int(player_id), [0, 0])


  def get_player_ids(self, game_type):
    # using both dicts is probably unnecessary
    return set(
        list(self._winloss(game_type).keys()) +
        list(self._ratings(game_type).keys()))


  def new_player(self, game_type, player_id):
    self.get_rating(game_type, player_id)
    self.get_winloss(game_type, player_id)
    self.get_killdeath(game_type, player_id)


  def load(self, file_name):
    # {'type': {'pid': [rating.mu, rating.sigma, win, loss], ...}, ...}
    json_data = json.loads(open(file_name).read())
    player_ids = set()

    for game_type in json_data:
      for player_id in json_data[game_type]:
        player_ids.add(player_id)

    for game_type in json_data:
      for player_id in player_ids:
        data = json_data[game_type][player_id]
        self.set_rating(
            game_type, player_id, trueskill.Rating(data[0], data[1]))
        self.set_winloss(game_type, player_id, [data[2], data[3]])
        self.set_killdeath(game_type, player_id, [data[4], data[5]])


  def save(self, file_name):
    game_types = set(
        list(self._ratings_dict.keys()) + list(self._winloss_dict.keys()))
    player_ids = set()
    for game_type in game_types:
      player_ids.update(self._ratings(game_type).keys())
      player_ids.update(self._winloss(game_type).keys())

    json_data = {}
    for game_type in game_types:
      data = json_data.setdefault(game_type, {})
      for player_id in player_ids:
        rating = self.get_rating(game_type, player_id)
        winloss = self.get_winloss(game_type, player_id)
        killdeath = self.get_killdeath(game_type, player_id)
        data[str(player_id)] = [
          rating.mu, rating.sigma,
          winloss[0], winloss[1],
          killdeath[0], killdeath[1]]

    open(file_name, 'w+').write(json.dumps(json_data, sort_keys=True, indent=2))



class oloraculo(minqlx.Plugin):
  def __init__(self):
    self.add_command('oloraculo', self.cmd_oloraculo)
    self.add_command('oloraculo_ratings', self.cmd_oloraculo_ratings)
    self.add_hook('game_end', self.handle_game_end)
    self.add_hook('game_start', self.handle_game_start)
    self.add_hook("player_loaded", self.handle_player_loaded)

    self.stats = Db()

    # Maps steam player_id to name:
    # {'player_id': 'name', ...}
    self.player_id_map = {}
    self.load_stats()

    # TESTING
    if TESTING:
      self.cmd_oloraculo(None, None, None)
      self.cmd_oloraculo_ratings(None, None, None)


  def load_stats(self):
    self.stats.load(JSON_FILE_PATH)
    self.print_log('Stats loaded.')


  def save_stats(self):
    self.stats.save(JSON_FILE_PATH)
    self.print_log('Stats saved.')


  def get_clean_name(self, name):
    return re.sub(r'([\W]*\]v\[[\W]*|^\W+|\W+$)', '', name).lower()


  def name_by_id(self, id):
    if id in self.player_id_map:
      return self.get_clean_name(self.player_id_map[id])
    else:
      return '...%s' % str(id)[8:]


  def get_player_ratings(self, player_id):
    return self.stats.get_rating(self.game.type_short, player_id)


  def get_match_qualities(self, players_present):
    players_per_team = int(len(players_present) / 2)
    teams = list(itertools.combinations(players_present, players_per_team))

    seen_matches = set()
    match_qualities = []

    for team_a in teams:
      for team_b in teams:
        match_key = repr(sorted((sorted(team_a), sorted(team_b))))

        if list(set(team_a) & set(team_b)) or match_key in seen_matches:
          continue

        seen_matches.add(match_key)

        team_a_ratings = [
          self.get_player_ratings(player_id) for player_id in team_a]
        team_b_ratings = [
          self.get_player_ratings(player_id) for player_id in team_b]

        quality = trueskill.quality([team_a_ratings, team_b_ratings])
        match_qualities.append([quality, [team_a, team_b]])

    return match_qualities


  def update_player_ratings(self):
    game_type = self.game.type_short

    teams = self.teams()
    red_ratings = []
    blue_ratings = []

    if len(teams['red']) == 0 or len(teams['blue']) == 0:
      return

    # Update win / loss
    for player in teams['red']:
      red_ratings.append(self.stats.get_rating(game_type, player.steam_id))
      if self.game.red_score > self.game.blue_score:
        self.stats.get_winloss(game_type, player.steam_id)[0] += 1
      else:
        self.stats.get_winloss(game_type, player.steam_id)[1] += 1

    for player in teams['blue']:
      blue_ratings.append(self.stats.get_rating(game_type, player.steam_id))
      if self.game.red_score < self.game.blue_score:
        self.stats.get_winloss(game_type, player.steam_id)[0] += 1
      else:
        self.stats.get_winloss(game_type, player.steam_id)[1] += 1

    # Update kill / death
    for player in teams['blue'] + teams['red']:
      steam_id = player.steam_id
      self.stats.get_killdeath(game_type, steam_id)[0] += player.stats.kills
      self.stats.get_killdeath(game_type, steam_id)[1] += player.stats.deaths

    if self.game.red_score > self.game.blue_score:
      ranks = [0, 1]
    elif self.game.red_score < self.game.blue_score:
      ranks = [1, 0]
    else:
      ranks = [0, 0]

    new_ratings = trueskill.rate([red_ratings, blue_ratings], ranks=ranks)
    deltas = {}

    # Update red
    for index, player in enumerate(teams['red']):
      steam_id = player.steam_id
      old_rating = self.stats.get_rating(game_type, steam_id)
      new_rating = new_ratings[0][index]
      deltas[steam_id] = new_rating.exposure - old_rating.exposure
      self.stats.set_rating(game_type, steam_id, new_rating)

    # Update blue
    for index, player in enumerate(teams['blue']):
      steam_id = player.steam_id
      old_rating = self.stats.get_rating(game_type, steam_id)
      new_rating = new_ratings[1][index]
      deltas[steam_id] = new_rating.exposure - old_rating.exposure
      self.stats.set_rating(game_type, steam_id, new_rating)

    self.print_match_rating_deltas(deltas)
    self.print_log('Stats updated.')


  def populate_player_id_map(self):
    for p in self.players():
      self.player_id_map[p.steam_id] = self.get_clean_name(p.clean_name)


  def is_interesting_game_type(self):
    return self.game.type_short in INTERESTING_GAME_TYPES


  def handle_game_start(self, data):
    """
    data is: {
      'CAPTURE_LIMIT': 8,
      'SERVER_TITLE': 'Lo]v[ushasho Dedicated QuakeLive Server',
      'FACTORY_TITLE': 'Lo]v[ushasho CTF',
      'FACTORY': 'lmctf',
      'PLAYERS': [
        {'NAME': 'BluesyQuaker', 'TEAM': 2, 'STEAM_ID': '76561198014448247'},
        {'NAME': 'Sarge', 'TEAM': 1, 'STEAM_ID': '0'},
        {'NAME': '(2) Sarge', 'TEAM': 1, 'STEAM_ID': '0'},
        {'NAME': '(3) Sarge', 'TEAM': 2, 'STEAM_ID': '0'}
      ],
      'FRAG_LIMIT': 50,
      'INSTAGIB': 0,
      'TRAINING': 0,
      'QUADHOG': 0,
      'GAME_TYPE': 'CTF',
      'MAP': 'duelingkeeps',
      'MATCH_GUID': '763294c5-21bd-4ae5-9151-eca283ed68bf',
      'MERCY_LIMIT': 0,
      'INFECTED': 0,
      'SCORE_LIMIT': 150,
      'TIME_LIMIT': 0,
      'ROUND_LIMIT': 10
    }
    """
    if not self.is_interesting_game_type():
      return

    self.populate_player_id_map()
    self.load_stats()


  def handle_game_end(self, data):
    """
    data is: {
      'ROUND_LIMIT': 10,
      'TIME_LIMIT': 0,
      'FACTORY': 'lmctf',
      'INFECTED': 0,
      'LAST_TEAMSCORER': 'BluesyQuaker',
      'MERCY_LIMIT': 0,
      'LAST_SCORER': 'Sarge',
      'FRAG_LIMIT': 50,
      'LAST_LEAD_CHANGE_TIME': 31650,
      'TSCORE1': 8,
      'RESTARTED': 0,
      'INSTAGIB': 0,
      'GAME_TYPE': 'CTF',
      'FIRST_SCORER':' BluesyQuaker',
      'QUADHOG': 0,
      'SERVER_TITLE': 'Lo]v[ushasho Dedicated QuakeLive Server',
      'MATCH_GUID': '29808700-0500-48be-aab8-59764b16041b',
      'FACTORY_TITLE': 'Lo]v[ushasho CTF',
      'EXIT_MSG': 'Capturelimit hit.',
      'TRAINING': 0,
      'SCORE_LIMIT': 150,
      'CAPTURE_LIMIT': 8,
      'ABORTED':False,
      'MAP': 'duelingkeeps',
      'TSCORE0': 0,
      'GAME_LENGTH': 303
    }
    """
    if not self.is_interesting_game_type():
      return

    if data['ABORTED']:
      self.print_log('Not updating ratings: game was aborted.')
      return

    game_type = self.game.type_short
    max_score = max(data['TSCORE0'], data['TSCORE1'])
    if game_type == 'ctf':
      limit = data['CAPTURE_LIMIT']
    elif game_type == 'ad':
      limit = data['SCORE_LIMIT']

    if max_score < limit:
      self.print_log('Not updating ratings: no team won.')
      return

    self.update_player_ratings()
    self.save_stats()


  def handle_player_loaded(self, player):
    player_id = player.steam_id
    game_type = self.game.type_short
    # Update name map, initialize ratings and winloss for new player.
    self.player_id_map[player_id] = self.get_clean_name(player.clean_name)
    self.stats.new_player(game_type, player_id)


  def print_header(self, message):
    self.msg('%s%s' % (HEADER_COLOR_STRING, '=' * 80))
    self.msg('%sOlorACulo v3.0:^7 %s' % (HEADER_COLOR_STRING, message))
    self.msg('%s%s' % (HEADER_COLOR_STRING, '-' * 80))


  def print_match_rating_deltas(self, deltas):
    self.print_header('match rating deltas (beta)')
    for player_id in deltas:
      name = self.name_by_id(player_id)
      self.msg('^5%12s^7: ^3%5.2f^7' % (name, deltas[player_id]))
    self.msg(' ')


  def print_player_ratings(self):

    def get_ratio_string(title, max_value, value_a, value_b):
      ratio = value_a / float(value_b) if value_b > 0 else 0.0
      fmt = '(^2%%%dd^7/^1%%%dd^7)' % (len(str(max_value)), len(str(max_value)))
      str_right = fmt % (value_a, value_b)
      return '%s: ^3%5.2f^7 %11s' % (title, ratio, str_right)

    game_type = self.game.type_short
    self.print_header('player ratings (%s)' % game_type)
    player_ids = self.stats.get_player_ids(game_type)

    line_data = []
    max_kd = 0
    max_wl = 0
    for player_id in player_ids:
      name = self.name_by_id(player_id)
      rating = self.stats.get_rating(game_type, player_id)
      winloss = self.stats.get_winloss(game_type, player_id)
      killdeath = self.stats.get_killdeath(game_type, player_id)
      max_kd = max(max_kd, max(killdeath))
      max_wl = max(max_wl, max(winloss))
      line_data.append([
          name, rating.exposure,
          winloss[0], winloss[1],
          killdeath[0], killdeath[1]])

    for player_name, exposure, win, loss, kill, death in sorted(
        line_data, key=lambda x:x[1], reverse=True):
      wl_str = get_ratio_string('wl', max_wl, win, loss)
      kd_str = get_ratio_string('kd', max_kd, kill, death)
      self.msg('^5%12s^7: ^3%5.2f^7 · %s · %s' % (
          player_name, exposure, wl_str, kd_str))
    self.msg(' ')


  def print_log(self, msg):
    self.msg('%sOlorACulo:^7 %s' % (HEADER_COLOR_STRING, msg))


  def cmd_oloraculo_ratings(self, player, msg, channel):
    if not self.is_interesting_game_type():
      self.print_log('This game type is not interesting. No ratings.')
      return

    self.populate_player_id_map()
    self.print_player_ratings()


  def cmd_oloraculo(self, player, msg, channel):
    if not self.is_interesting_game_type():
      self.print_log('This game type is not interesting. No predictions.')
      return

    game_type = self.game.type_short
    self.populate_player_id_map()
    players_present = [
        p.steam_id for p in self.players() if p.team in ['red', 'blue']]

    if TESTING:
      players_present = PRESENT_TEST
      self.player_id_map = PLAYER_ID_MAP_TEST

    if len(players_present) > 1:
      match_qualities = self.get_match_qualities(players_present)
      self.print_header('predictions (%s)' % self.game.type_short)
      for match in sorted(match_qualities, reverse=True)[:4]:
        red = ', '.join([self.name_by_id(id) for id in match[1][0]])
        blue = ', '.join([self.name_by_id(id) for id in match[1][1]])
        # BluesyQuaker on blue:
        if 76561198014448247 in match[1][0]:
          red, blue = blue, red
        self.msg('^3%.4f^7 : ^1%s ^7vs ^4%s^7' % (match[0], red, blue))
      self.msg(' ')

    else:
      self.print_log('Cannot predict with less than 2 players.')

    if TESTING:
      self.save_stats()
