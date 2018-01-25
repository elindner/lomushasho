import datetime
import copy
import itertools
import json
import minqlx
import os
import pprint
import re


HEADER_COLOR_STRING = '^2'
JSON_FILE_NAME = 'funes_history.json'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_FILE_PATH = os.path.join(ROOT_PATH, JSON_FILE_NAME)


class funes(minqlx.Plugin):
  def __init__(self):
    # List: [['yyyy-ww', 'gt', [r_ids], [b_ids], r_score, b_score], ...]
    self.history = None
    self.load_history()
    self.add_command('funes', self.cmd_funes, 2)
    self.add_hook('game_start', self.handle_game_start)
    self.add_hook("player_loaded", self.handle_player_loaded)

    # Maps steam player_id to name:
    # {'player_id': 'name', ...}
    self.player_id_map = {}

  def print_log(self, msg):
    self.msg('%sFunes:^7 %s' % (HEADER_COLOR_STRING, msg))

  def get_clean_name(self, name):
    return re.sub(r'([\W]*\]v\[[\W]*|^\W+|\W+$)', '', name).lower()

  def get_week_key(self):
    iso = datetime.date.today().isocalendar()
    return '-'.join([str(iso[0]), '%02d' % iso[1]])

  def get_team_key(self, team):
    return ':'.join(sorted([str(p.steam_id) for p in team]))

  def get_match_key(self, team_a, team_b):
    return 'v'.join(
        sorted([self.get_team_key(team_a), self.get_team_key(team_b)]))

  def populate_player_id_map(self):
    for p in self.players():
      self.player_id_map[p.steam_id] = self.get_clean_name(p.clean_name)

  def print_header(self, message):
    self.msg('%s%s' % (HEADER_COLOR_STRING, '=' * 80))
    self.msg('%sFunes v1.0:^7 %s' % (HEADER_COLOR_STRING, message))
    self.msg('%s%s' % (HEADER_COLOR_STRING, '-' * 80))

  def load_history(self):
    try:
      self.history = json.loads(open(JSON_FILE_PATH).read())
      self.print_log('Loaded history.')
    except Exception as e:
      self.print_log('Could not load history (%s)' % e)
      self.history = {}

  def save_history(self):
    open(JSON_FILE_PATH, 'w+').write(
        json.dumps(self.history, sort_keys=True, indent=2))
    self.print_log('History saved.')

  def get_history(self):
    return copy.deepcopy(self.history)

  def name_by_id(self, id):
    if id in self.player_id_map:
      return self.get_clean_name(self.player_id_map[id])
    else:
      return '...%s' % str(id)[8:]

  def get_teams_history(self, game_type, teams, aggregate=False):
    relevant_matches = []
    week_key = self.get_week_key()
    team_0_ids = sorted(teams[0])
    team_1_ids = sorted(teams[1])

    history = [0, 0]
    for match in self.history:
      if not aggregate and match[0] != week_key:
        # don't need this date
        continue

      if not (team_0_ids in match and team_1_ids in match):
        # wrong teams
        continue

      team_0_score = match[match.index(team_0_ids) + 2]
      team_1_score = match[match.index(team_1_ids) + 2]
      if team_0_score > team_1_score:
        history[0] += 1
      elif team_0_score < team_1_score:
        history[1] += 1

    return history

  def handle_player_loaded(self, player):
    player_id = player.steam_id
    # Update name map, initialize ratings and winloss for new player.
    self.player_id_map[player_id] = self.get_clean_name(player.clean_name)

  def handle_game_start(self, data):
    self.load_history()
    self.populate_player_id_map()

    teams = self.teams()
    red_team = teams['red']
    blue_team = teams['blue']
    if len(red_team) == 0 or len(blue_team) == 0:
      return

    game_type = self.game.type_short
    red_ids = [p.steam_id for p in red_team]
    blue_ids = [p.steam_id for p in blue_team]

    history = self.get_teams_history(game_type, [red_ids, blue_ids])
    aggregate = self.get_teams_history(
        game_type, [red_ids, blue_ids], aggregate=True)

    red_names = ', '.join(
        sorted([self.get_clean_name(p.clean_name) for p in red_team]))
    blue_names = ', '.join(
        sorted([self.get_clean_name(p.clean_name) for p in blue_team]))

    self.print_header('teams history (%s)' % game_type)
    self.msg('    Today: ^1%s^7 ^3%d^7 v ^3%d^7 ^4%s^7' % (
        red_names, history[0], history[1], blue_names))
    self.msg(' Historic: ^1%s^7 ^3%d^7 v ^3%d^7 ^4%s^7' % (
        red_names, aggregate[0], aggregate[1], blue_names))

  def handle_game_end(self, data):
    if data['ABORTED']:
      self.print_log('Not updating history: game was aborted.')
      return

    game_type = self.game.type_short
    max_score = max(data['TSCORE0'], data['TSCORE1'])
    if game_type == 'ctf':
      limit = data['CAPTURE_LIMIT']
    elif game_type == 'ad':
      limit = data['SCORE_LIMIT']
    else:
      limit = data['FRAG_LIMIT']

    if max_score < limit:
      self.print_log('Not updating history: no team won.')
      return

    teams = self.teams()
    red_team = teams['red']
    blue_team = teams['blue']
    if len(red_team) == 0 or len(blue_team) == 0:
      self.print_log('Not updating history: one or more empty teams.')
      return

    datum = [
        self.get_week_key(),
        game_type,
        sorted([p.steam_id for p in red_team]),
        sorted([p.steam_id for p in blue_team]),
        self.game.red_score,
        self.game.blue_score]

    self.history.append(datum)
    self.print_log('History updated.')
    self.save_history()

  def cmd_funes(self, player, msg, channel):
    self.populate_player_id_map()
    game_type = self.game.type_short
    players_present = [
        p.steam_id for p in self.players() if p.team in ['red', 'blue']]

    names_by_id = dict(zip(
        players_present,
        [p.clean_name for p in self.players() if p.team in ['red', 'blue']]))

    if len(players_present) < 2:
      self.print_log('No history for less than 2 players.')
      return

    players_per_team = int(len(players_present) / 2)
    teams = list(itertools.combinations(players_present, players_per_team))
    seen_matches = set()
    day_line_data = []
    aggregated_line_data = []

    for team_a in teams:
      for team_b in teams:
        match_key = repr(sorted((sorted(team_a), sorted(team_b))))
        if list(set(team_a) & set(team_b)) or match_key in seen_matches:
          continue

        seen_matches.add(match_key)
        names_a = ', '.join([names_by_id[i] for i in team_a])
        names_b = ', '.join([names_by_id[i] for i in team_b])
        history = self.get_teams_history(game_type, (team_a, team_b))
        aggregate = self.get_teams_history(game_type, (team_a, team_b),
                                           aggregate=True)
        day_line_data.append((names_a, history[0], history[1], names_b))
        aggregated_line_data.append(
            (names_a, aggregate[0], aggregate[1], names_b))

    self.print_header('Teams history (%s)' % game_type)
    self.msg('Today:')
    for data in day_line_data:
      self.msg('^3%24s  ^2%d  ^7v  ^2%d  ^3%s' % data)

    self.msg('%s%s' % (HEADER_COLOR_STRING, '-' * 80))
    self.msg('Since %s:' % (self.history[0][0].replace('-', 'w')))
    for data in aggregated_line_data:
      self.msg('^3%24s  ^2%d  ^7v  ^2%d  ^3%s' % data)
