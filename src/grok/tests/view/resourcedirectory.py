"""
You can explicitly specify the resource directory using grok.resources on module level:

  >>> grok.grok(__name__)

  >>> manfred = Mammoth()
  >>> from zope.publisher.browser import TestRequest
  >>> request = TestRequest()
  >>> from zope import component
  >>> view = component.getMultiAdapter((manfred, request), name='food')
  >>> print view()
  <html>
  <body>
  ME GROK EAT MAMMOTH!
  </body>
  </html>

"""
import grok

grok.resources('resourcedirectoryname')

class Mammoth(grok.Model):
    pass
