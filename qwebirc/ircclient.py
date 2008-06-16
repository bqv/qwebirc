import twisted, sys
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.web import resource, server
from twisted.protocols import basic

import hmac, time, config
from config import HMACTEMPORAL
HMACKEY = hmac.HMAC(key=config.HMACKEY)

def hmacfn(*args):
  h = HMACKEY.copy()
  h.update("%d %s" % (int(time.time() / HMACTEMPORAL), " ".join(args)))
  return h.hexdigest()

class QWebIRCClient(basic.LineReceiver):
  delimiter = "\n"
  
  def dataReceived(self, data):
    basic.LineReceiver.dataReceived(self, data.replace("\r", ""))

  def lineReceived(self, line):
    line = irc.lowDequote(line)
    try:
      line = line.decode("utf-8")
    except UnicodeDecodeError:
      line = line.decode("iso-8859-1", "ignore")
    
    try:
      prefix, command, params = irc.parsemsg(line)
      self.handleCommand(command, prefix, params)
    except irc.IRCBadMessage:
      self.badMessage(line, *sys.exc_info())
        
  def badMessage(self, args):
    self("badmessage", args)
  
  def handleCommand(self, command, prefix, params):
    self("c", command, prefix, params)
    
  def __call__(self, *args):
    self.factory.publisher.event(args)
    
  def write(self, data):
    self.transport.write("%s\r\n" % irc.lowQuote(data.encode("utf-8")))
      
  def connectionMade(self):
    basic.LineReceiver.connectionMade(self)
    
    f = self.factory.ircinit
    nick, ident, ip, realname = f["nick"], f["ident"], f["ip"], f["realname"]
    
    hmac = hmacfn(ident, ip)
    self.write("USER %s bleh bleh %s %s :%s" % (ident, ip, hmac, realname))
    self.write("NICK %s" % nick)
    
    self.factory.client = self
    self("connect")

  def connectionLost(self, reason):
    self.factory.client = None
    basic.LineReceiver.connectionLost(self, reason)
    self("disconnect")
    
class QWebIRCFactory(protocol.ClientFactory):
  protocol = QWebIRCClient
  def __init__(self, publisher, **kwargs):
    self.client = None
    self.publisher = publisher
    self.ircinit = kwargs
    
  def write(self, data):
    self.client.write(data)
    
def createIRC(*args, **kwargs):
  f = QWebIRCFactory(*args, **kwargs)
  reactor.connectTCP(config.IRCSERVER, config.IRCPORT, f)
  return f

if __name__ == "__main__":
  e = createIRC(lambda x: 2, nick="slug__moo", ident="mooslug", ip="1.2.3.6", realname="mooooo")
  reactor.run()