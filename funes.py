import datetime
import copy
import minqlx
import json
import os
import re


HEADER_COLOR_STRING = '^2'
JSON_FILE_NAME = 'funes_history.json'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_FILE_PATH = os.path.join(ROOT_PATH, JSON_FILE_NAME)

class funes(minqlx.Plugin):
  def __init__(self):
    self.history = None
    self.load_history()
    self.add_command('funes', self.cmd_funes, 2)
    self.add_hook('game_start', self.handle_game_start)

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


  def load_history(self):
    try:
      self.history = json.loads(open(JSON_FILE_PATH).read())
      self.print_log('Loaded history.')
    except Exception as e:
      self.print_log('Could not load history (%s)' % e)
      self.history = {}


  def print_header(self, message):
    self.msg('%s%s' % (HEADER_COLOR_STRING, '=' * 80))
    self.msg('%sFunes v1.0:^7 %s' % (HEADER_COLOR_STRING, message))
    self.msg('%s%s' % (HEADER_COLOR_STRING, '-' * 80))


  def save_history(self):
    open(JSON_FILE_PATH, 'w+').write(
        json.dumps(self.history, sort_keys=True, indent=2))
    self.print_log('History saved.')


  def get_history(self):
    return copy.deepcopy(self.history)


  def print_history(self, channel):
    self.print_header(channel, 'History')
    channel.reply(' ')


  def populate_player_id_map(self):
    for p in self.players():
      self.player_id_map[p.steam_id] = self.get_clean_name(p.clean_name)


  def get_teams_history(self, game_type, teams, aggregate=False):
    game_type_history = self.history.setdefault(game_type, {})
    match_key = self.get_match_key(teams['red'], teams['blue'])
    week_key = self.get_week_key()
    week_history = game_type_history.setdefault(week_key, {})
    teams_history = week_history.setdefault(match_key, [0, 0])

    if not aggregate:
      return teams_history

    # Return all history
    history = [0, 0]
    for week in game_type_history:
      for match in game_type_history[week]:
        if match == match_key:
          history[0] += game_type_history[week][match][0]
          history[1] += game_type_history[week][match][1]

    return history


  def handle_game_start(self, data):
    self.populate_player_id_map()
    self.load_history()

    teams = self.teams()
    red_team = teams['red']
    blue_team = teams['blue']
    if len(red_team) == 0 or len(blue_team) == 0:
      return

    game_type = self.game.type_short

    match_key = self.get_match_key(blue_team, red_team)
    red_key = self.get_team_key(red_team)
    history = self.get_teams_history(game_type, teams)
    aggregate = self.get_teams_history(game_type, teams, aggregate=True)
    red_index = 0 if match_key.startswith(red_key) else 1

    red_wins = history[red_index]
    blue_wins = history[1 - red_index]
    red_wins_historic = aggregate[red_index]
    blue_wins_historic = aggregate[1 - red_index]

    red_names = ', '.join(
        sorted([self.get_clean_name(p.clean_name) for p in red_team]))
    blue_names = ', '.join(
        sorted([self.get_clean_name(p.clean_name) for p in blue_team]))

    self.print_header('teams history (%s)' % game_type)
    self.msg('    Today: ^1%s^7 ^3%d^7 v ^3%d^7 ^4%s^7' % (
        red_names, red_wins, blue_wins, blue_names))
    self.msg(' Historic: ^1%s^7 ^3%d^7 v ^3%d^7 ^4%s^7' % (
        red_names, red_wins_historic, blue_wins_historic, blue_names))


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

    teams_history = self.get_teams_history(game_type, teams)

    match_key = self.get_match_key(red_team, blue_team)
    red_key = self.get_team_key(red_team)
    red_index = 0 if match_key.startswith(red_key) else 1

    if self.game.red_score > self.game.blue_score:
      teams_history[red_index] += 1
    else:
      teams_history[1 - red_index] += 1

    self.print_log('History updated.')
    self.save_history()


  def cmd_funes(self, player, msg, channel):
    pass

