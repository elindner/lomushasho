import re


class PlayerStats(object):
  def __init__(self, kills, deaths):
    self.kills = kills
    self.deaths = deaths


class Player(object):
  def __init__(self, steam_id, name, team=None, kills=0, deaths=0):
    self.steam_id = steam_id
    self.name = name
    self.clean_name = name
    self.team = team
    self.stats = PlayerStats(kills, deaths)

  def __repr__(self):
    return 'Player<%d:%s(%s)>' % (self.steam_id, self.name, self.team)


class Game(object):
  def __init__(self, type_short, red_score=0, blue_score=0):
    self.type_short = type_short
    self.red_score = red_score
    self.blue_score = blue_score


class Plugin(object):
  registered_commands = []
  registered_hooks = []
  messages = []
  current_map_name = None
  current_factory = None
  game = Game('ad')
  players_by_team = {}

  def reset():
    Plugin.registered_commands = []
    Plugin.registered_hooks = []
    Plugin.messages = []
    Plugin.current_map_name = None
    Plugin.current_factory = None
    Plugin.game = Game('ad')
    Plugin.players_by_team = {}

  def set_game(game):
    Plugin.game = game

  def set_players_by_team(players_by_team):
    for team in players_by_team:
      for player in players_by_team[team]:
        player.team = team
    Plugin.players_by_team = players_by_team

  # minqlx.Plugin API here:

  def teams(self):
    return self.players_by_team.copy()

  def players(self):
    return [player for team in self.players_by_team.values() for player in team]

  def msg(self, message):
    clean_message = re.sub(r'\^[\d]', '', message)
    Plugin.messages.append(clean_message)

  def add_command(self, name, cmd, arg_count=0):
    Plugin.registered_commands.append([name, cmd, arg_count])

  def add_hook(self, event, handler, priority=None):
    Plugin.registered_hooks.append([event, handler, priority])

  def change_map(self, map_name, factory):
    Plugin.current_map_name = map_name
    Plugin.current_factory = factory


class Channel(object):
  message_log = ''

  def reset():
    Channel.message_log = ''

  # minqlx.Plugin API here:

  def reply(self, message):
    clean_message = re.sub(r'\^[\d]', '', message)
    Channel.message_log = '%s\n%s' % (Channel.message_log, clean_message)


def reset():
  Plugin.reset()
  Channel.reset()


def call_command(command, *args, **kwargs):
  channel = Channel()
  command(None, [None] + list(args), channel)
