from setuptools import setup, find_packages
import os

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description = (
    read('README.txt')
    + '\n' +
    read('CHANGES.txt')
    + '\n' +
    'Download\n'
    '********\n'
    )

tests_require = [
    'zope.app.wsgi',
    'zope.configuration',
    'zope.testing',
    ]

setup(
    name='grok',
    version = '1.1dev',
    author='Grok Team',
    author_email='grok-dev@zope.org',
    url='http://grok.zope.org',
    download_url='http://cheeseshop.python.org/pypi/grok/',
    description='Grok: Now even cavemen can use Zope 3!',
    long_description=long_description,
    license='ZPL',
    classifiers=['Environment :: Web Environment',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: Zope Public License',
                 'Programming Language :: Python',
                 'Framework :: Zope3',
                 ],

    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data = True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'ZODB3',
        'grokcore.annotation >= 1.1',
        'grokcore.component >= 1.5, < 2.0',
        'grokcore.content',
        'grokcore.formlib >= 1.4',
        'grokcore.security >= 1.1',
        'grokcore.site',
        'grokcore.view >= 1.12',
        'grokcore.viewlet >= 1.3',
        'martian >= 0.10, < 0.12',
        'pytz',
        'simplejson',
        'z3c.autoinclude',
        'z3c.flashmessage',
        'z3c.testsetup',
        'zc.catalog',
        'zope.annotation',
        'zope.app.appsetup',
        'zope.app.http',
        'zope.app.pagetemplate',
        'zope.app.publication',
        'zope.browserpage',
        'zope.catalog',
        'zope.component',
        'zope.container',
        'zope.contentprovider',
        'zope.copypastemove',
        'zope.dottedname',
        'zope.event',
        'zope.exceptions',
        'zope.formlib',
        'zope.i18n',
        'zope.i18nmessageid',
        'zope.interface',
        'zope.intid',
        'zope.keyreference',
        'zope.lifecycleevent',
        'zope.location',
        'zope.pagetemplate',
        'zope.password',
        'zope.pluggableauth',
        'zope.principalregistry',
        'zope.proxy',
        'zope.publisher',
        'zope.schema',
        'zope.security',
        'zope.securitypolicy',
        'zope.site',
        'zope.size',
        'zope.traversing',
        'zope.viewlet',
        ],
    tests_require=tests_require,
    extras_require={'test': tests_require},
)
