##############################################################################
#
# Copyright (c) 2006-2007 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Grok components"""

import os
import persistent
import datetime
import warnings
import pytz
import simplejson

import zope.location
from zope import component
from zope import interface
from zope.interface.common import idatetime
from zope.securitypolicy.role import Role
from zope.publisher.browser import BrowserPage
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces.http import IHTTPRequest
from zope.publisher.publish import mapply
from zope.formlib import form
from zope.annotation.interfaces import IAttributeAnnotatable

from zope.app.publisher.browser import getDefaultViewName
from zope.app.container.btree import BTreeContainer
from zope.app.container.contained import Contained
from zope.app.container.interfaces import IReadContainer, IObjectAddedEvent
from zope.app.container.interfaces import IOrderedContainer
from zope.app.container.contained import notifyContainerModified
from persistent.list import PersistentList
from zope.app.component.site import SiteManagerContainer
from zope.app.component.site import LocalSiteManager

from zope.viewlet.manager import ViewletManagerBase
from zope.viewlet.viewlet import ViewletBase

import grok
import grokcore.view
import z3c.flashmessage.interfaces
import martian.util

from grok import interfaces, util
from grokcore.view import formlib
from grokcore.view import GrokForm
from grokcore.view import PageTemplate
from grokcore.view import PageTemplateFile


class Model(Contained, persistent.Persistent):
    # XXX Inheritance order is important here. If we reverse this,
    # then containers can't be models anymore because no unambigous MRO
    # can be established.
    interface.implements(IAttributeAnnotatable, interfaces.IContext)


class Container(BTreeContainer):
    interface.implements(IAttributeAnnotatable, interfaces.IContainer)


class OrderedContainer(Container):
    interface.implements(IOrderedContainer)

    def __init__(self):
        super(OrderedContainer, self).__init__()
        self._order = PersistentList()

    def keys(self):
        # Return a copy of the list to prevent accidental modifications.
        return self._order[:]

    def __iter__(self):
        return iter(self.keys())

    def values(self):
        return (self[key] for key in self._order)

    def items(self):
        return ((key, self[key]) for key in self._order)

    def __setitem__(self, key, object):
        foo = self.has_key(key)
        # Then do whatever containers normally do.
        super(OrderedContainer, self).__setitem__(key, object)
        if not foo:
            self._order.append(key)

    def __delitem__(self, key):
        # First do whatever containers normally do.
        super(OrderedContainer, self).__delitem__(key)
        self._order.remove(key)

    def updateOrder(self, order):
        if set(order) != set(self._order):
            raise ValueError("Incompatible key set.")

        self._order = PersistentList()
        self._order.extend(order)
        notifyContainerModified(self)


class Site(SiteManagerContainer):
    pass

@component.adapter(Site, IObjectAddedEvent)
def addSiteHandler(site, event):
    sitemanager = LocalSiteManager(site)
    # LocalSiteManager creates the 'default' folder in its __init__.
    # It's not needed anymore in new versions of Zope 3, therefore we
    # remove it
    del sitemanager['default']
    site.setSiteManager(sitemanager)


class Application(Site):
    """A top-level application object."""
    interface.implements(interfaces.IApplication)


class LocalUtility(Model):
    pass


class Annotation(persistent.Persistent):
    pass

# all grok tests pass when this is commented out
#
#class ViewBase(object):
#    def __init__(self, context, request):
#        self.context = context
#        self.request = request

class View(BrowserPage, grokcore.view.ViewMixin):
    interface.implements(interfaces.IGrokView)

    def __init__(self, context, request):
        BrowserPage.__init__(self, context, request)
        grokcore.view.ViewMixin.__init__(self, context, request)

    def __call__(self):
        return self._update_and_render()

    def default_namespace(self):
        namespace = {}
        namespace['context'] = self.context
        namespace['request'] = self.request
        namespace['static'] = self.static
        namespace['view'] = self
        return namespace

    def __getitem__(self, key):
        # This is BBB code for Zope page templates only:
        if not isinstance(self.template, PageTemplate):
            raise AttributeError("View has no item %s" % key)

        value = self.template._template.macros[key]
        # When this deprecation is done with, this whole __getitem__ can
        # be removed.
        warnings.warn("Calling macros directly on the view is deprecated. "
                      "Please use context/@@viewname/macros/macroname\n"
                      "View %r, macro %s" % (self, key),
                      DeprecationWarning, 1)
        return value

    def flash(self, message, type='message'):
        source = component.getUtility(
            z3c.flashmessage.interfaces.IMessageSource, name='session')
        source.send(message, type)

    def application_url(self, name=None):
        obj = self.context
        while obj is not None:
            if isinstance(obj, Application):
                return self.url(obj, name)
            obj = obj.__parent__
        raise ValueError("No application found.")


class XMLRPC(object):
    pass

class REST(zope.location.Location):
    interface.implements(interfaces.IREST)

    def __init__(self, context, request):
        self.context = self.__parent__ = context
        self.request = request
        self.body = request.bodyStream.getCacheStream().read()

    @property
    def response(self):
        return self.request.response

##     def GET(self):
##         raise GrokMethodNotAllowed(self.context, self.request)

##     def POST(self):
##         raise GrokMethodNotAllowed(self.context, self.request)

##     def PUT(self):
##         raise GrokMethodNotAllowed(self.context, self.request)

##     def DELETE(self):
##         raise GrokMethodNotAllowed(self.context, self.request)

class JSON(BrowserPage):

    def __call__(self):
        view_name = self.__view_name__
        method = getattr(self, view_name)
        method_result = mapply(method, (), self.request)
        return simplejson.dumps(method_result)


class Traverser(object):
    interface.implements(IBrowserPublisher)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def browserDefault(self, request):
        # if we have a RESTful request, we will handle
        # GET, POST and HEAD differently (PUT and DELETE are handled already
        # but not on the BrowserRequest layer but the HTTPRequest layer)
        if IRESTLayer.providedBy(request):
            rest_view = component.getMultiAdapter(
                (self.context, self.request),
                name=request.method)
            return rest_view, ()
        view_name = getDefaultViewName(self.context, request)
        view_uri = "@@%s" % view_name
        return self.context, (view_uri,)

    def publishTraverse(self, request, name):
        subob = self.traverse(name)
        if subob is not None:
            return util.safely_locate_maybe(subob, self.context, name)

        traversable_dict = grok.traversable.bind().get(self.context)
        if traversable_dict:
            if name in traversable_dict:
                subob = getattr(self.context, traversable_dict[name])
                if callable(subob):
                    subob = subob()
                return util.safely_locate_maybe(subob, self.context, name)

        # XXX Special logic here to deal with containers.  It would be
        # good if we wouldn't have to do this here. One solution is to
        # rip this out and make you subclass ContainerTraverser if you
        # wanted to override the traversal behaviour of containers.
        if IReadContainer.providedBy(self.context):
            item = self.context.get(name)
            if item is not None:
                return item

        view = component.queryMultiAdapter((self.context, request), name=name)
        if view is not None:
            return view

        raise NotFound(self.context, name, request)

    def traverse(self, name):
        # this will be overridden by subclasses
        pass


class ContextTraverser(Traverser):
    component.adapts(interfaces.IContext, IHTTPRequest)

    def traverse(self, name):
        traverse = getattr(self.context, 'traverse', None)
        if traverse:
            return traverse(name)


class ContainerTraverser(Traverser):
    component.adapts(interfaces.IContainer, IHTTPRequest)

    def traverse(self, name):
        traverse = getattr(self.context, 'traverse', None)
        if traverse:
            result = traverse(name)
            if result is not None:
                return result
        # try to get the item from the container
        return self.context.get(name)


default_form_template = PageTemplateFile(os.path.join(
    'templates', 'default_edit_form.pt'))
default_form_template.__grok_name__ = 'default_edit_form'
default_display_template = PageTemplateFile(os.path.join(
    'templates', 'default_display_form.pt'))
default_display_template.__grok_name__ = 'default_display_form'

class Form(GrokForm, form.FormBase, View):
    # We're only reusing the form implementation from zope.formlib, we
    # explicitly don't want to inherit the interface semantics (mostly
    # for the different meanings of update/render).
    interface.implementsOnly(interfaces.IGrokForm)

    template = default_form_template

    def applyData(self, obj, **data):
        return formlib.apply_data_event(obj, self.form_fields, data,
                                        self.adapters)

    # BBB -- to be removed in June 2007
    def applyChanges(self, obj, **data):
        warnings.warn("The 'applyChanges' method on forms is deprecated "
                      "and will disappear by June 2007. Please use "
                      "'applyData' instead.", DeprecationWarning, 2)
        return bool(self.applyData(obj, **data))


class AddForm(Form):
    pass


class EditForm(GrokForm, form.EditFormBase, View):
    # We're only reusing the form implementation from zope.formlib, we
    # explicitly don't want to inherit the interface semantics (mostly
    # for the different meanings of update/render).
    interface.implementsOnly(interfaces.IGrokForm)

    template = default_form_template

    def applyData(self, obj, **data):
        return formlib.apply_data_event(obj, self.form_fields, data,
                                        self.adapters, update=True)

    # BBB -- to be removed in June 2007
    def applyChanges(self, obj, **data):
        warnings.warn("The 'applyChanges' method on forms is deprecated "
                      "and will disappear by June 2007. Please use "
                      "'applyData' instead.", DeprecationWarning, 2)
        return bool(self.applyData(obj, **data))

    @formlib.action("Apply")
    def handle_edit_action(self, **data):
        if self.applyData(self.context, **data):
            formatter = self.request.locale.dates.getFormatter(
                'dateTime', 'medium')

            try:
                time_zone = idatetime.ITZInfo(self.request)
            except TypeError:
                time_zone = pytz.UTC

            self.status = "Updated on %s" % formatter.format(
                datetime.datetime.now(time_zone)
                )
        else:
            self.status = 'No changes'


class DisplayForm(GrokForm, form.DisplayFormBase, View):
    # We're only reusing the form implementation from zope.formlib, we
    # explicitly don't want to inherit the interface semantics (mostly
    # for the different meanings of update/render).
    interface.implementsOnly(interfaces.IGrokForm)

    template = default_display_template


class IndexesClass(object):
    def __init__(self, name, bases=(), attrs=None):
        if attrs is None:
            return
        indexes = {}
        for name, value in attrs.items():
            # Ignore everything that's not an index definition object
            # except for values set by directives
            if '.' in name:
                setattr(self, name, value)
                continue
            if not interfaces.IIndexDefinition.providedBy(value):
                continue
            indexes[name] = value
        self.__grok_indexes__ = indexes
        # __grok_module__ is needed to make defined_locally() return True for
        # inline templates
        self.__grok_module__ = martian.util.caller_module()

Indexes = IndexesClass('Indexes')

Public = 'zope.Public'

class Role(Role):
    pass

class IRESTLayer(interface.Interface):
    pass

class RESTProtocol(object):
    pass

class ViewletManager(ViewletManagerBase):
    interface.implements(interfaces.IViewletManager)

    template = None

    def __init__(self, context, request, view):
        super(ViewletManager, self).__init__(context, request, view)
        self.context = context
        self.request = request
        self.view = view
        self.__name__ = self.__view_name__
        self.static = component.queryAdapter(
            self.request,
            interface.Interface,
            name=self.module_info.package_dotted_name
            )

    def sort(self, viewlets):
        """Sort the viewlets.

        ``viewlets`` is a list of tuples of the form (name, viewlet).
        """
        # In Grok, the default order of the viewlets is determined by
        # util.sort_components. util.sort_components() however expects
        # a list of just components, but sort() is supposed to deal
        # with a list of (name, viewlet) tuples.
        # To handle this situation we first store the name part on the
        # viewlet, then use util.sort_components() and then "unpack"
        # the name from the viewlet and recreate the list of (name,
        # viewlet) tuples, now in the correct order.
        s_viewlets = []
        for name, viewlet in viewlets:
            # Stuff away viewlet name so we can later retrieve it.
            # XXX We loose name information in case the same viewlet
            # is in the viewlets list twice, but with a different
            # name. Most probably this situation doesn't occur.
            viewlet.__viewlet_name__ = name
            s_viewlets.append(viewlet)
        s_viewlets = util.sort_components(s_viewlets)
        return [(viewlet.__viewlet_name__, viewlet) for viewlet in s_viewlets]

    def default_namespace(self):
        namespace = {}
        namespace['context'] = self.context
        namespace['request'] = self.request
        namespace['static'] = self.static
        namespace['view'] = self.view
        namespace['viewletmanager'] = self
        return namespace

    def namespace(self):
        return {}

    def render(self):
        """See zope.contentprovider.interfaces.IContentProvider"""
        # Now render the view
        if self.template:
            return self.template.render(self)
        else:
            return u'\n'.join([viewlet.render() for viewlet in self.viewlets])


class Viewlet(ViewletBase):
    """Batteries included viewlet.
    """

    def __init__(self, context, request, view, manager):
        super(Viewlet, self).__init__(context, request, view, manager)
        self.context = context
        self.request = request
        self.view = view
        self.viewletmanager = manager
        self.__name__ = self.__view_name__
        self.static = component.queryAdapter(
            self.request,
            interface.Interface,
            name=self.module_info.package_dotted_name
            )

    def default_namespace(self):
        namespace = {}
        namespace['context'] = self.context
        namespace['request'] = self.request
        namespace['static'] = self.static
        namespace['view'] = self.view
        namespace['viewlet'] = self
        namespace['viewletmanager'] = self.manager
        return namespace

    def namespace(self):
        return {}

    def update(self):
        pass

    def render(self):
        return self.template.render(self)
