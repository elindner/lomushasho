import minqlx
import json
import os

HEADER_COLOR_STRING = '^2'
JSON_FILE_NAME = 'mapuche_aliases.json'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_FILE_PATH = os.path.join(ROOT_PATH, JSON_FILE_NAME)


class mapuche(minqlx.Plugin):

  def __init__(self):
    self.load_aliases()

    self.add_command('mapuche', self.cmd_mapuche, 2)
    self.add_command('mapuche_aliases', self.cmd_mapuche_aliases)
    self.add_command('mapuche_set', self.cmd_mapuche_set, 2)
    self.add_command('mapuche_reload', self.cmd_mapuche_reload, 2)
    self.add_command('mapuche_remove', self.cmd_mapuche_remove, 2)

  def print_log(self, msg):
    self.msg('%sMapuche:^7 %s' % (HEADER_COLOR_STRING, msg))

  def load_aliases(self):
    self.aliases = None
    try:
      self.aliases = json.loads(open(JSON_FILE_PATH).read())
      self.print_log('Loaded %d aliases.' % len(self.aliases.keys()))
    except Exception as e:
      self.print_log('Could not load aliases (%s)' % e)
      self.aliases = {}

  def print_header(self, channel, message):
    channel.reply('%s%s' % (HEADER_COLOR_STRING, '=' * 80))
    channel.reply('%sMapuche v1.0:^7 %s' % (HEADER_COLOR_STRING, message))
    channel.reply('%s%s' % (HEADER_COLOR_STRING, '-' * 80))

  def save_aliases(self):
    open(JSON_FILE_PATH, 'w+').write(
        json.dumps(self.aliases, sort_keys=True, indent=2))

  def get_aliases(self):
    return self.aliases.copy()

  def print_aliases(self, channel):
    self.print_header(channel, 'Aliases')
    for alias in self.aliases:
      mapname = self.aliases[alias]['mapname']
      factory = self.aliases[alias]['factory']
      channel.reply('^5%20s^7 : ^3%s^7 (%s)' % (alias, mapname, factory))
    channel.reply(' ')

  def print_commands(self, channel):
    channel.reply('^5!mapuche <alias> [factory]^7: change map with alias.')
    channel.reply('^5!mapuche_set <alias> <map> <factory>^7: set alias.')
    channel.reply('^5!mapuche_remove <alias>^7: remove alias.')
    channel.reply('^5!mapuche_reload^7: reoload aliases from disk cache.')
    channel.reply('^5!mapuche_aliases^7: list aliases.')
    channel.reply(' ')

  def print_aliases_and_commands(self, channel):
    self.print_aliases(channel)
    self.print_commands(channel)

  def cmd_mapuche(self, player, msg, channel):
    if len(msg) < 2 or msg[1] not in self.aliases:
      self.print_aliases_and_commands(channel)
      return

    alias = msg[1]
    map_name = self.aliases[alias]['mapname']
    factory = msg[2] if len(msg) > 2 else self.aliases[alias]['factory']

    self.print_log('Changing map to \"^5%s^7\" (\"%s\")' % (alias, map_name))
    self.change_map(map_name, factory)

  def cmd_mapuche_set(self, player, msg, channel):
    if len(msg) < 4:
      self.print_aliases_and_commands(channel)
      return

    alias = msg[1]
    map_name = msg[2]
    factory = msg[3]
    self.aliases[alias] = {'mapname': map_name, 'factory': factory}
    self.save_aliases()

  def cmd_mapuche_reload(self, player, msg, channel):
    self.load_aliases()

  def cmd_mapuche_remove(self, player, msg, channel):
    if len(msg) < 2:
      self.print_aliases_and_commands(channel)
      return

    self.aliases.pop(msg[1], None)
    self.save_aliases()

  def cmd_mapuche_aliases(self, player, msg, channel):
    self.print_aliases(channel)
