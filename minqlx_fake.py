class Player(object):
  def __init__(self, steam_id, name):
    self.steam_id = steam_id
    self.name = name
    self.clean_name = name


class Game(object):
  def __init__(self, type_short):
    self.type_short = type_short


class Plugin(object):
  registered_commands = []
  registered_hooks = []
  last_message = None
  current_map_name = None
  current_factory = None
  game = Game('ad')

  def reset():
    Plugin.registered_commands = []
    Plugin.registered_hooks = []
    Plugin.last_message = None
    Plugin.current_map_name = None
    Plugin.current_factory = None
    Plugin.game = Game('ad')

  def msg(self, message):
    Plugin.last_message = message

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

  def reply(self, message):
    Channel.message_log = '%s\n%s' % (Channel.message_log, message)


def reset():
  Plugin.reset()
  Channel.reset()


def call_command(command, *args, **kwargs):
  channel = Channel()
  command(None, [None] + list(args), channel)

