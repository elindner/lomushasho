import os
import re

ANSI_COLOR_MAP = {
    '^0': '\u001b[30m',  # black
    '^1': '\u001b[31m',  # red
    '^2': '\u001b[32m',  # green
    '^3': '\u001b[33m',  # yellow
    '^4': '\u001b[34m',  # blue
    '^5': '\u001b[36m',  # cyan
    '^6': '\u001b[35m',  # magenta
    '^7': '\u001b[37m',  # white
}

PRINT_ANSI = ('CONSOLE_OUTPUT' in os.environ and
              os.environ['CONSOLE_OUTPUT'].lower() == 'true')

PRI_LOWEST = 1000


def print_ansi(message):
  global PRINT_ANSI
  if not PRINT_ANSI:
    return
  ansi_message = message
  for quake_color, ansi_color in ANSI_COLOR_MAP.items():
    ansi_message = ansi_message.replace(quake_color, ansi_color)
  print(ansi_message + ANSI_COLOR_MAP['^7'])


class PlayerStats(object):

  def __init__(self, kills, deaths):
    self.kills = kills
    self.deaths = deaths


class Player(object):

  def __init__(self,
               steam_id,
               name,
               team=None,
               kills=0,
               deaths=0,
               ip=None,
               ping=None):
    self.messages = []
    self.steam_id = steam_id
    self.name = name
    self.clean_name = name
    self.team = team
    self.stats = PlayerStats(kills, deaths)
    self.ip = ip
    self.ping = ping

  def __repr__(self):
    return 'Player<%d:%s(%s)>' % (self.steam_id, self.name, self.team)

  def clear_messages(self):
    self.messages = []

  # minqlx.Plugin API here:

  def put(self, team):
    self.team = team

  def tell(self, message):
    self.messages.append(re.sub(r'\^[\d]', '', message))
    print_ansi(message)


class Game(object):

  def __init__(self,
               type_short,
               map_name=None,
               red_score=0,
               blue_score=0,
               aborted=False):
    self.type_short = type_short
    self.red_score = red_score
    self.blue_score = blue_score
    self.aborted = aborted
    self.map = map_name

  def __repr__(self):
    return 'game<%s:%d-%d%s>' % (self.type_short, self.red_score,
                                 self.blue_score,
                                 '(aborted)' if self.aborted else '')


class Db(object):

  def __init__(self):
    self.flags = {}

  def get_flag(self, player, flag, default=False):
    if not flag in self.flags:
      return default
    return self.flags[flags]


class Plugin(object):
  registered_commands = []
  registered_hooks = []
  messages = []
  is_dev_map = False
  current_factory = None
  game = Game('ad')
  players_by_team = {}
  players_list = []
  db = Db()

  def reset():
    Plugin.registered_commands = []
    Plugin.registered_hooks = []
    Plugin.messages = []
    Plugin.sounds_played = {}
    Plugin.is_dev_map = False
    Plugin.current_factory = None
    Plugin.game = Game('ad')
    Plugin.players_by_team = {}
    Plugin.players_list = []
    Plugin.cvars = {}

  def set_game(game):
    Plugin.game = game

  def reset_log():
    Plugin.messages = []

  def set_players_by_team(players_by_team):
    for team in players_by_team:
      for player in players_by_team[team]:
        player.team = team
        Plugin.players_list.append(player)
    Plugin.players_by_team = players_by_team

  def set_map(map_name):
    Plugin.game.map = map_name

  # minqlx.Plugin API here:

  def teams(self):
    return self.players_by_team.copy()

  def players(self):
    return [player for team in self.players_by_team.values() for player in team]

  def player(self, steam_id):
    for player in Plugin.players_list:
      if player.steam_id == steam_id:
        return player
    return None

  def msg(self, message):
    print_ansi(message)
    clean_message = re.sub(r'\^[\d]', '', message)
    Plugin.messages.append(clean_message)

  def add_command(self, name, cmd, arg_count=0):
    Plugin.registered_commands.append([name, cmd, arg_count])

  def add_hook(self, event, handler, priority=None):
    Plugin.registered_hooks.append([event, handler, priority])

  def change_map(self, map_name, factory, dev=False):
    Plugin.game.map = map_name
    Plugin.is_dev_map = dev
    Plugin.current_factory = factory

  def clean_text(self, text):
    return re.compile(r"\^[^\^]").sub("", text)

  def play_sound(self, sound_file, player):
    Plugin.sounds_played.setdefault(player, [])
    return Plugin.sounds_played[player].append(sound_file)

  def get_cvar(self, cvar, cvar_type):
    return cvar_type(Plugin.cvars[cvar])

  def set_cvar(self, cvar, value):
    Plugin.cvars[cvar] = value


def console_command(cmd_line):
  tokens = cmd_line.split(' ')
  cmd = tokens[0]
  if cmd == 'devmap':
    Plugin.game.map = tokens[1]
    Plugin.is_dev_map = True
    Plugin.current_factory = tokens[2]


def delay(time):
  return lambda x: x


def reset():
  Plugin.reset()


def load_player(player):
  run_game_hooks('player_loaded', player=player)


def send_chat(player, msg):
  run_game_hooks('chat', player=player, msg=msg, channel='chat')


# def run_game_hooks(event, data=None):
def run_game_hooks(event, **kwargs):
  hooks = [h for h in Plugin.registered_hooks if h[0] == event]
  if not hooks:
    return
  for hook in hooks:
    handler = hook[1]
    handler(**kwargs)


def end_game():
  run_game_hooks('game_end',
                 data={
                     'MAP': Plugin.game.map,
                     'TSCORE0': Plugin.game.red_score,
                     'TSCORE1': Plugin.game.blue_score,
                     'SCORE_LIMIT': 15,
                     'CAPTURE_LIMIT': 8,
                     'ABORTED': Plugin.game.aborted,
                 })


def countdown_game():
  run_game_hooks('game_countdown')


def start_game(player_id_map,
               map_name,
               red_team_ids,
               blue_team_ids,
               red_score,
               blue_score,
               aborted=False):
  setup_game_data(player_id_map, map_name, red_team_ids, blue_team_ids,
                  red_score, blue_score, aborted)
  run_game_hooks('game_start',
                 data={
                     'MAP': Plugin.game.map,
                     'TSCORE0': Plugin.game.red_score,
                     'TSCORE1': Plugin.game.blue_score,
                     'SCORE_LIMIT': 15,
                     'CAPTURE_LIMIT': 8,
                     'ABORTED': Plugin.game.aborted,
                 })


def run_game(player_id_map,
             map_name,
             red_team_ids,
             blue_team_ids,
             red_score,
             blue_score,
             aborted=False):
  start_game(player_id_map, map_name, red_team_ids, blue_team_ids, red_score,
             blue_score, aborted)
  end_game()


def frame():
  run_game_hooks('frame')


def setup_game_data(player_id_map,
                    map_name,
                    red_team_ids,
                    blue_team_ids,
                    red_score,
                    blue_score,
                    aborted=False):
  players_by_teams = {'red': [], 'blue': []}
  for player_id in red_team_ids:
    players_by_teams['red'].append(player_id_map[player_id])
  for player_id in blue_team_ids:
    players_by_teams['blue'].append(player_id_map[player_id])

  Plugin.set_game(Game('ad', map_name, red_score, blue_score, aborted))
  Plugin.set_players_by_team(players_by_teams)


def call_command(command_string, player=None):
  if not command_string.startswith('!'):
    return

  parts = command_string[1:].split(' ')
  command_name = parts[0]
  arguments = [None] + parts[1:]

  commands = [c for c in Plugin.registered_commands if c[0] == command_name]
  for command in commands:
    fun = command[1]
    fun(player, arguments, None)
