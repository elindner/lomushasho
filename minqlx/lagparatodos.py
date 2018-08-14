import minqlx
import os
import re

HEADER_COLOR_STRING = '^2'
CONFIG_FILE_NAME = 'lag_para_todos.config'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE_PATH = os.path.join(ROOT_PATH, CONFIG_FILE_NAME)


class lagparatodos(minqlx.Plugin):

  def __init__(self):
    self.add_command('lagparatodos', self.cmd_lagparatodos, 1)

  def print_header(self, message):
    self.msg('%s%s' % (HEADER_COLOR_STRING, '=' * 80))
    self.msg(
        '%sLagParaTodos (y Todas) v6.66:^7 %s' % (HEADER_COLOR_STRING, message))
    self.msg('%s%s' % (HEADER_COLOR_STRING, '-' * 80))

  def print_log(self, msg):
    self.msg('%sLagParaTodos:^7 %s' % (HEADER_COLOR_STRING, msg))

  def get_clean_name(self, name):
    return re.sub(r'([\W]*\]v\[[\W]*|^\W+|\W+$)', '', name).lower()

  def cmd_lagparatodos(self, player, msg, channel):
    if len(msg) < 2 or msg[1] not in ('set', 'remove'):
      player.tell('Format: ^5!lagparatodos^7 <set|remove> [whitelist]')
      return

    command = msg[1]
    whitelist = msg[2].split(',') if len(msg) == 3 else []

    if command == 'remove':
      open(CONFIG_FILE_PATH, 'w').close()
      self.print_log('Rules ^3removed^7. Back to normal.')
      return

    players = [p for p in self.players() if p.team in ['red', 'blue']]
    if len(players) < 2:
      self.print_log(
          'There should be at least two players. ^3Nothing changed^7.')
      return

    max_ping = max([p.ping for p in players if p.ip not in whitelist])
    entries = sorted(
        [[
            self.get_clean_name(p.clean_name),
            p.ip,
            p.ping if p.ip not in whitelist else max_ping,
        ] for p in players],
        key=lambda x: (x[2], 1 if x[1] not in whitelist else 0))

    self.print_header('Generating rules. Max ping is ^1%dms^7' % max_ping)
    lines = []
    for entry in entries:
      added_ping = max_ping - entry[2]
      ip = entry[1]
      name = entry[0]

      added_message = ''
      if ip in whitelist:
        added_message = '------ whitelisted'
      elif added_ping == 0:
        added_message = '------ baseline'
      else:
        added_message = '^3%4dms^7 added' % added_ping

      self.msg('^5%20s^7: %s' % (name, added_message))

      lines.append('%s:%d\n' % (ip, added_ping))

    config_file = open(CONFIG_FILE_PATH, 'w')
    config_file.writelines(lines)
    self.msg('')
    self.msg('Rules ^3set^7. Enjoy your lag! ^1>:[^7')

    config_file.close()
