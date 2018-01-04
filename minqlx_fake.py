class Plugin(object):
  registered_commands = []
  last_message = None
  current_map_name = None
  current_factory = None

  def reset():
    Plugin.registered_commands = []
    Plugin.last_message = None
    Plugin.current_map_name = None
    Plugin.current_factory = None

  def msg(self, message):
    Plugin.last_message = message

  def add_command(self, name, cmd, arg_count=0):
    Plugin.registered_commands.append([name, cmd, arg_count])

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

