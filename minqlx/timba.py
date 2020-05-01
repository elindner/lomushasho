import copy
import itertools
import json
import minqlx
import os
import re
import threading
import time

HEADER_COLOR_STRING = '^2'
JSON_FILE_NAME = 'timba_credits.json'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_FILE_PATH = os.path.join(ROOT_PATH, JSON_FILE_NAME)
STARTING_CREDITS = 5000
INTERESTING_GAME_TYPES = ['ad', 'ctf']
BETTING_WINDOW_SECS = 30


class timba(minqlx.Plugin):

  def __init__(self):
    self.betting_timer = None
    self.betting_window_end_time = 0
    self.reminder_timers = []
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

  def print_log(self, msg):
    self.msg('%sTimba:^7 %s' % (HEADER_COLOR_STRING, msg))

  def print_error(self, msg):
    self.msg('%sTimba:^1 %s' % (HEADER_COLOR_STRING, msg))

  def print_header(self, message):
    self.msg('%s%s' % (HEADER_COLOR_STRING, '=' * 80))
    self.msg('%sTimba v0.01:^7 %s' % (HEADER_COLOR_STRING, message))
    self.msg('%s%s' % (HEADER_COLOR_STRING, '-' * 80))

  def is_interesting_game_type(self):
    return self.game.type_short in INTERESTING_GAME_TYPES

  def is_betting_window_open(self):
    return self.betting_timer and self.betting_timer.is_alive()

  def get_clean_name(self, name):
    return re.sub(r'([\W]*\]v\[[\W]*|^\W+|\W+$|[^a-zA-Z0-9\ ]+.+\W$)', '',
                  name).lower().strip()

  def get_current_bets(self):
    return self.current_bets

  def get_credits(self):
    return self.credits

  def get_betting_timer(self):
    return self.betting_timer

  def load_credits(self):
    try:
      credits = json.loads(open(JSON_FILE_PATH).read())
      for key, value in credits.items():
        self.credits[int(key)] = value

      self.print_log('Loaded credits for %s players.' %
                     len(self.credits.keys()))
    except Exception as e:
      self.print_error('Could not load credits (%s)' % e)

  def save_credits(self):
    open(JSON_FILE_PATH,
         'w+').write(json.dumps(self.credits, sort_keys=True, indent=2))
    self.print_log('Credits saved.')

  def print_bets(self, bets, winners, losers):
    self.print_header('Bets for this game:')
    if bets:
      for player_id in winners + losers:
        # for player_id, bet in self.current_bets.items():
        bet = bets[player_id]
        amount = bet['amount'] if player_id in winners else -bet['amount']
        clean_name = self.get_clean_name(self.names_by_id[player_id])
        amount_color = '^2' if player_id in winners else '^1'
        msg_string = '^5%30s^7 : %s%5d^7 on %-4s' % (clean_name, amount_color,
                                                     amount, bet['team'])
        msg_string = msg_string.replace('on red', 'on ^1red^7')
        msg_string = msg_string.replace('on blue', 'on ^4blue^7')
        self.msg(msg_string)

  def get_pot(self, bets):
    return sum([bet['amount'] for bet in bets.values()])

  def close_betting_window(self):
    pot = self.get_pot(self.current_bets)
    pot_msg = ('The pot is ^3%d^7 credits.' %
               pot) if pot > 0 else ('There were no bets.')
    self.print_log('Betting is now closed. %s' % pot_msg)

    for player_id, bet in self.current_bets.items():
      self.credits[player_id] -= bet['amount']
      player = self.player(player_id)
      if (player):
        team = '^1red^7' if bet['team'] == 'red' else '^4blue^7'
        self.player(player_id).tell(
            ('You bet ^3%d^7 credits on team %s. You have ^3%d^7 credits left. '
             + 'Good luck!') % (bet['amount'], team, self.credits[player_id]))

  def stop_timers(self):
    self.betting_timer.cancel()
    for timer in self.reminder_timers:
      timer.cancel()

  def betting_reminder(self):
    self.print_log('You have ^3%d^7 seconds to place your bets!' %
                   (self.betting_window_end_time - int(time.time())))

  def handle_game_start(self, data):
    if self.is_betting_window_open():
      self.betting_reminder()

  def handle_game_countdown(self):
    if not self.is_interesting_game_type():
      return

    if self.is_betting_window_open():
      # Why would this happen?
      self.print_error('Countdown started while betting is open. Why?')
      self.stop_timers()

    self.betting_window_end_time = int(time.time()) + BETTING_WINDOW_SECS
    self.betting_timer = threading.Timer(BETTING_WINDOW_SECS,
                                         self.close_betting_window)

    # Setup a couple of reminders
    self.reminder_timers = [
        threading.Timer(BETTING_WINDOW_SECS - 10, self.betting_reminder),
        threading.Timer(BETTING_WINDOW_SECS - 5, self.betting_reminder),
    ]
    for timer in self.reminder_timers:
      timer.start()

    self.betting_timer.start()
    self.print_log(
        'Betting is now open: you have ^3%d^7 seconds to place your bets!' %
        BETTING_WINDOW_SECS)

  def handle_game_end(self, data):
    bets = copy.deepcopy(self.current_bets)
    self.current_bets = {}

    # If the window has been closed, we already took credits
    # from bettors, so we should return it
    if data['ABORTED'] and not self.is_betting_window_open():
      for player_id, bet in bets.items():
        self.credits[player_id] += bet['amount']

    # Should not be necessary, but anyways:
    self.stop_timers()

    if data['ABORTED']:
      self.print_log('No one wins: game was aborted.')
      return

    if self.is_betting_window_open():
      self.print_error('The betting window never closed!')
      return

    pot = self.get_pot(bets)
    if not self.is_interesting_game_type() or pot == 0:
      self.print_log('No one wins: There were no bets.')
      return

    winner = 'red' if self.game.red_score > self.game.blue_score else 'blue'
    loser = 'red' if winner == 'blue' else 'blue'

    bets_teams = set([bet['team'] for bet in bets.values()])

    if bets_teams == {winner}:
      # all bets to the winner, just reset their credits
      for player_id, bet in bets.items():
        self.credits[player_id] += bet['amount']
      self.print_log(
          'When everyone wins, no one wins: everyone bet on the winner.')
      self.save_credits()
      return

    if bets_teams == {loser}:
      # all bets to the loser, do nothing
      self.print_log('Everyone bet on the loser.')
      self.save_credits()
      return

    winner_bets_total = sum(
        [bet['amount'] for bet in bets.values() if bet['team'] == winner])

    winner_ids = [
        player_id for player_id in bets.keys()
        if bets[player_id]['team'] == winner
    ]
    loser_ids = list(bets.keys() - winner_ids)

    # dict: {player_id: {'team': ('red'|'blue'), 'amount': amount}, ...}
    for player_id in winner_ids:
      bet = bets[player_id]
      ratio = bet['amount'] / winner_bets_total
      win = round(pot * ratio)
      new_credits = self.credits.setdefault(player_id, STARTING_CREDITS) + win
      player = self.player(player_id)
      if player:
        player.tell('YOU ^2WON^7 ^3%d^7 CREDITS. You now have ^3%d^7 credits.' %
                    (win, new_credits))
      self.credits[player_id] = new_credits

    for player_id in loser_ids:
      player = self.player(player_id)
      if player:
        player.tell(
            'YOU ^1LOST^7 ^3%d^7 CREDITS. You have ^3%d^7 credits left.' %
            (bets[player_id]['amount'], self.credits[player_id]))

    self.print_bets(bets, winner_ids, loser_ids)
    self.save_credits()

  def parse_bet(self, msg):
    if len(msg) < 3:
      return None

    valid_teams = ['b', 'blue', 'r', 'red']

    if msg[1].isdigit():
      amount = msg[1]
      team = msg[2]
    elif msg[2].isdigit():
      amount = msg[2]
      team = msg[1]
    else:
      return None

    if team not in valid_teams:
      return None

    return {'team': 'red' if team[0] == 'r' else 'blue', 'amount': int(amount)}

  def cmd_timba(self, player, msg, channel):
    if not self.is_interesting_game_type():
      player.tell('You can only bet on these game types: %s.' %
                  (', '.join(INTERESTING_GAME_TYPES)))
      return

    player_id = player.steam_id
    self.names_by_id[player_id] = self.get_clean_name(player.clean_name)
    current_credits = self.credits.setdefault(player_id, STARTING_CREDITS)

    if not self.is_betting_window_open():
      player.tell(
          'Betting is not allowed now. You have ^3%d^7 credits to bet.' %
          current_credits)
      return

    if len(msg) == 1:
      player.tell('You have ^3%d^7 credits to bet.' % current_credits)
      return

    bet = self.parse_bet(msg)
    if not bet:
      player.tell('To bet: ^5!timba (red|blue) <amount>^7. ' +
                  'You have ^3%d^7 credits to bet.' % current_credits)
      return

    team = bet['team']
    amount = bet['amount']

    if current_credits < amount:
      player.tell('^1You only have ^3%d^1 credits to bet.' % current_credits)
      return

    if amount == 0 and player_id in self.current_bets:
      self.current_bets.pop(player_id, None)
      player.tell('You removed your bet.')
      return

    # dict: {player_id: {'team': ('red'|'blue'), 'amount': amount}, ...}
    self.current_bets[player_id] = bet

    team = '^1red^7' if team == 'red' else '^4blue^7'
    time_left = self.betting_window_end_time - int(time.time())
    player.tell(('You bet ^3%d^7 credits on team %s. ' +
                 'You have ^3%d^7 seconds to change your bet.') %
                (amount, team, time_left))
