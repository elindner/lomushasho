import minqlx
import os

HEADER_COLOR_STRING = '^2'
CONFIG_FILE_NAME = 'lag_para_todos.config'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE_PATH = os.path.join(ROOT_PATH, CONFIG_FILE_NAME)


class lagparatodos(minqlx.Plugin):

  def __init__(self):
    self.add_command('lagparatodos', self.cmd_lagparatodos, 1)

  def print_log(self, msg):
    self.msg('%sLagParaTodos:^7 %s' % (HEADER_COLOR_STRING, msg))

  def cmd_lagparatodos(self, player, msg, channel):
    if len(msg) < 2 or msg[1] not in ('set', 'remove'):
      player.tell('Format: ^5!lagparatodos^7 <set|remove>')
      player.tell(' ')
      return

    command = msg[1]

    config_file = open(CONFIG_FILE_PATH, 'w')
    if command == 'set':
      players = self.players()
      max_ping = max([p.ping for p in players])
      lines = ['%s:%d' % (p.ip, max_ping - p.ping) for p in players]
      config_file.writelines(lines)
      self.print_log(
          'Rules ^3set^7. Max ping is %dms. Enjoy your lag.' % max_ping)
    else:
      self.print_log('Rules ^3removed^7. Back to normal.')

    config_file.close()
