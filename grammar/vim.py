from dragonfly import (Grammar, AppContext, CompoundRule, Choice, Dictation, List, Optional, Literal, Context, MappingRule, IntegerRef)
import natlink, os, time

from proxy_nicknames import Key, Text

from comsat import ComSat

from raul import SelfChoice, processDictation, NUMBERS as numbers

class VimContext(Context):
  def __init__(self):
    self._str = "VimContext"

  def matches(self, executable, title, handle):
    with ComSat() as cs:
      active_title = cs.getRPCProxy().callGetState()["active_title"]
      if active_title:
        active_title = active_title.strip().lower()
      else:
        return False

      return (active_title.startswith("vim ") or active_title.endswith(" vim") or
              " vim " in active_title)

grammar_context = AppContext(executable="notepad") & VimContext()
grammar = Grammar("vim", context=grammar_context)

class EasyMotion(CompoundRule):
  spec = "<command> [<end>] [<inout>]"
  command = SelfChoice("command", ["leap", "jump"])
  end = SelfChoice("end", ["start", "end"])
  inout = SelfChoice("inout", ["in", "out"])

  extras = [command, end, inout]

  def _process_recognition(self, node, extras):
    command = str(extras["command"])
    location = str(extras.get("end", "start"))
    inout = str(extras.get("inout", "in"))

    shortcut = {("leap", "start"):"b",
                ("leap", "end"):"ge",
                ("jump", "start"):"w",
                ("jump", "end"):"e"}[(command, location)]

    (Key("Escape, backslash:2") + Text(shortcut)).execute()

class VimSearch(CompoundRule):
  spec = "vim <cmd> [<number>]"
  cmd = {"query":"/", "query back":"?",
         "search":"/", "search back":"?"}
  extras = [SelfChoice("cmd", cmd), SelfChoice("number", numbers)]

  def _process_recognition(self, node, extras):
    number = int(numbers.get(str(extras.get("number", "one")), "1"))
    with ComSat() as cs:
      rpc = cs.getRPCProxy()
      rpc.callKeys("Escape")
      cmd = self.cmd[str(extras["cmd"])]
      rpc.callText("%i%s" % (number, cmd))
      if "search" in str(extras["cmd"]):
        rpc.callKeys(["Return"])
    if "search" in str(extras["cmd"]):
      Text("i").execute()

class VimCommand(CompoundRule):
  spec = "vim <cmd>"
  cmd = {"write":"w", "write and quit":"wq", "quit bang":"q!", "quit":"q",
         "undo":"u", "redo":":redo"}
  extras = [SelfChoice("cmd", cmd)]

  def _process_recognition(self, node, extras):
    with ComSat() as cs:
      rpc = cs.getRPCProxy()
      rpc.callKeys("Escape")
      cmd = self.cmd[str(extras["cmd"])]
      rpc.callText(":%s\n" % cmd)
    if cmd == "w":
      time.sleep(0.2) # vim does not seem to notice the keystroke unless it occurs after the save is complete
      Key("i").execute()

class GoCommand(MappingRule):
  mapping = {"<n> go":Key("Escape") + Text("%(n)dGi")}
  extras = [IntegerRef("n", 1, 1000)] #  for longer files i can just use manual keystroke commands

grammar.add_rule(EasyMotion())
grammar.add_rule(VimCommand())
grammar.add_rule(VimSearch())
grammar.add_rule(GoCommand())

grammar.load()

def unload():
  global grammar
  if grammar: grammar.unload()
  grammar = None
