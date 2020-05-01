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
    self.msg('%sLagParaTodos (y Todas) v6.66:^7 %s' %
             (HEADER_COLOR_STRING, message))
    self.msg('%s%s' % (HEADER_COLOR_STRING, '-' * 80))

  def print_log(self, msg):
    self.msg('%sLagParaTodos:^7 %s' % (HEADER_COLOR_STRING, msg))

  def get_clean_name(self, name):
    return re.sub(r'([\W]*\]v\[[\W]*|^\W+|\W+$|[^a-zA-Z0-9\ ]+.+\W$)', '',
                  name).lower().strip()

  def parse_params(self, msg):
    is_ip = lambda s: len(
        [p for p in s.split('.') if p.isdigit() and int(p) <= 255]) == 4

    if len(msg) < 2 or msg[1] not in ('set', 'remove'):
      # wasn't given a command.
      return None

    params = {
        'command': msg[1],
        'whitelist': [],
        'latency_limit': None,
    }

    if params['command'] == 'remove':
      return params

    for raw_param in msg[1:]:
      if raw_param.isdigit():
        params['latency_limit'] = int(raw_param)
      else:
        ip_list = [p for p in raw_param.split(',') if is_ip(p)]
        if ip_list:
          params['whitelist'] = ip_list

    return params

  def cmd_lagparatodos(self, player, msg, channel):
    params = self.parse_params(msg)
    if not params:
      player.tell(
          'Format: ^5!lagparatodos^7 <set|remove> [whitelist] [latency_limit]')
      return

    command = params['command']
    whitelist = params['whitelist']
    latency_limit = params['latency_limit']

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
    if latency_limit:
      max_ping = min(max_ping, latency_limit)

    entries = sorted([[
        self.get_clean_name(p.clean_name),
        p.ip,
        p.ping if p.ip not in whitelist else max_ping,
    ] for p in players],
                     key=lambda x: (x[2], 1 if x[1] not in whitelist else 0))

    self.print_header('Generating rules. Max ping is ^1%dms^7' % max_ping)
    lines = []
    for entry in entries:
      added_ping = max(0, max_ping - entry[2])
      ip = entry[1]
      name = entry[0]

      added_message = ''
      if ip in whitelist:
        added_message = '------ whitelisted'
      elif added_ping == 0:
        added_message = '------ over limit'
      else:
        added_message = '^3%4dms^7 added' % added_ping

      self.msg('^5%20s^7: %s' % (name, added_message))

      lines.append('%s:%d\n' % (ip, added_ping))

    config_file = open(CONFIG_FILE_PATH, 'w')
    config_file.writelines(lines)
    self.msg('')
    self.msg('Rules ^3set^7. Enjoy your lag! ^1>:[^7')

    config_file.close()
