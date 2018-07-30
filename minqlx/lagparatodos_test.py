import minqlx_fake
import sys
import unittest

sys.modules['minqlx'] = minqlx_fake
import lagparatodos


class TestLagParaTodos(unittest.TestCase):

  def setUp(self):
    minqlx_fake.reset()

  def test_registers_commands_and_hooks(self):
    lpt = lagparatodos.lagparatodos()
    self.assertEqual(['lagparatodos'],
                     [cmd[0] for cmd in minqlx_fake.Plugin.registered_commands])


if __name__ == '__main__':
  unittest.main()
