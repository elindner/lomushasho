class State():
  registered_commands = []
  last_message = None
  current_map_name = None
  current_factory = None


class Plugin(object):
  def msg(self, message):
    State.last_message = message

  def add_command(self, name, cmd, arg_count=0):
    State.registered_commands.append([name, cmd, arg_count])

  def change_map(self, map_name, factory):
    State.current_map_name = map_name
    State.current_factory = factory


def reset():
  State.registered_commands = []
  State.last_message = None
  State.current_map_name = None
  State.current_factory = None

