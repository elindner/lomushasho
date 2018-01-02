registered_commands = []
last_message = None

class Plugin(object):
  def msg(self, message):
    last_message = message

  def add_command(self, name, cmd, arg_count=0):
    registered_commands.append([name, cmd, arg_count])

def reset():
  global registered_commands
  global last_message
  registered_commands = []
  last_message = None

