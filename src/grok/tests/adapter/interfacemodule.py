"""
You can also specify interfaces instead of classes with
`grok.context` (module-level):

  >>> grok.grok(__name__)

  >>> cave = Cave()
  >>> home = IHome(cave)

  >>> IHome.providedBy(home)
  True
  >>> isinstance(home, Home)
  True

  >>> hole = Hole()
  >>> home = IHome(hole)

  >>> IHome.providedBy(home)
  True
  >>> isinstance(home, Home)
  True

"""
import grok
from zope import interface

class ICave(interface.Interface):
    pass

class Cave(grok.Model):
    grok.implements(ICave)

class Hole(grok.Model):
    grok.implements(ICave)

grok.context(ICave)

class IHome(interface.Interface):
    pass

class Home(grok.Adapter):
    grok.implements(IHome)
