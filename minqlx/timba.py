import datetime
import copy
import itertools
import json
import minqlx
import os
import pprint
import re

HEADER_COLOR_STRING = '^2'
JSON_FILE_NAME = 'timba_credits.json'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_FILE_PATH = os.path.join(ROOT_PATH, JSON_FILE_NAME)
STARTING_CREDITS = 5000


class timba(minqlx.Plugin):

  def __init__(self):
    self.betting_open = False
    # dict: {player_id: {'team': ('red'|'blue'), 'amount': amount}, ...}
    self.current_bets = {}
    # dict: {player_id: credits, ...}
    self.credits = {}
    # dict: {player_id: clean_name, ...}
    self.names_by_id = {}
    self.load_credits()

    self.add_command('timba', self.cmd_timba, 3)
    self.add_hook('game_countdown', self.handle_game_countdown)
    self.add_hook('game_start', self.handle_game_start)
    self.add_hook('game_end', self.handle_game_end)

  def print_msg(self, msg, channel=None):
    if channel:
      channel.reply(msg)
    else:
      self.msg(msg)

  def print_log(self, msg, channel=None):
    self.print_msg('%sTimba:^7 %s' % (HEADER_COLOR_STRING, msg), channel)

  def print_error(self, msg, channel=None):
    self.print_msg('%sTimba:^1 %s' % (HEADER_COLOR_STRING, msg), channel)

  def print_header(self, message):
    self.print_msg('%s%s' % (HEADER_COLOR_STRING, '=' * 80))
    self.print_msg('%sTimba v0.00001:^7 %s' % (HEADER_COLOR_STRING, message))
    self.print_msg('%s%s' % (HEADER_COLOR_STRING, '-' * 80))

  def get_clean_name(self, name):
    return re.sub(r'([\W]*\]v\[[\W]*|^\W+|\W+$)', '', name).lower()

  def get_current_bets(self):
    return self.current_bets

  def get_credits(self):
    return self.credits

  def load_credits(self):
    try:
      credits = json.loads(open(JSON_FILE_PATH).read())
      for key, value in credits.items():
        self.credits[int(key)] = value

      self.print_log(
          'Loaded credits for %s players.' % len(self.credits.keys()))
    except Exception as e:
      self.print_error('Could not load credits (%s)' % e)

  def save_credits(self):
    open(JSON_FILE_PATH, 'w+').write(
        json.dumps(self.credits, sort_keys=True, indent=2))
    self.print_log('Credits saved.')

  def handle_game_countdown(self, data):
    self.betting_open = True

  def print_bets(self):
    self.print_header('Bets for this game')
    if self.current_bets:
      for player_id, bet in self.current_bets.items():
        clean_name = self.get_clean_name(self.names_by_id[player_id])
        self.print_msg(
            '%30s : %5d on %-4s' % (clean_name, bet['amount'], bet['team']))

  # Workaround for invalid (empty?) teams() data on start, see:
  # https://github.com/MinoMino/minqlx-plugins/blob/96ef6f4ff630128a6c404ef3f3ca20a60c9bca6c/ban.py#L940
  @minqlx.delay(1)
  def handle_game_start(self, data):
    self.betting_open = False

  def handle_game_end(self, data):
    self.betting_open = False

    if data['ABORTED']:
      self.current_bets = {}
      self.print_log('No one wins: game was aborted.')
      return

    # dict: {player_id: {'team': ('red'|'blue'), 'amount': amount}, ...}
    winner = 'red' if self.game.red_score > self.game.blue_score else 'blue'

    for player_id, bet in self.current_bets.items():
      delta = bet['amount'] if bet['team'] == winner else -bet['amount']
      self.credits[player_id] = (self.credits.setdefault(
          player_id, STARTING_CREDITS)) + delta

    self.print_bets()
    self.save_credits()
    self.current_bets = {}

  def cmd_timba(self, player, msg, channel):
    player_id = player.steam_id
    self.names_by_id[player_id] = self.get_clean_name(player.clean_name)
    current_credits = self.credits.setdefault(player_id, STARTING_CREDITS)

    if not self.betting_open:
      self.print_error('You can only bet during warmup.', channel)
      return

    valid_teams = ['red', 'blue']

    if len(msg) == 1:
      self.print_log('You have %d credits to bet.' % current_credits, channel)
      return

    if len(msg) < 3 or msg[1] not in valid_teams or not msg[2].isdigit():
      self.print_log('To bet: !timba (red|blue) <amount>', channel)
      return

    team = msg[1]
    amount = int(msg[2])

    if current_credits < amount:
      self.print_log('^1You only have %d credits to bet.' % current_credits,
                     channel)
      return

    if amount == 0 and player_id in self.current_bets:
      self.current_bets.pop(player_id, None)
      self.print_log('You removed your bet.', channel)
      return

    # dict: {player_id: {'team': ('red'|'blue'), 'amount': amount}, ...}
    self.current_bets[player_id] = {
        'team': team,
        'amount': amount,
    }

    self.print_log('You bet %d credits on team %s.' % (amount, team), channel)
