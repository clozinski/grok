from setuptools import setup, find_packages

setup(
    name='grokdocs',
    version='0.1',
    author='Grok Team',
    author_email='grok-dev@zope.org',
    url='http://svn.zope.org/grok/trunk',
    description="""\
Grokdocs: Build the Grok documentation in different formats!
""",
    install_requires=['docutils==0.4',
                      'zope.pagetemplate',
                      'zope.app.renderer',
                      'Sphinx==0.1.61950',
                      'Pygments',
                      'ulif.rest',
                      ],
    package_dir = {'': 'src'},
    packages=find_packages('src'),
    entry_points="""
    [console_scripts]
    grokdocs2html = grokdocs.grokdocs:render
    grokdocs2latex = grokdocs.grokdocs:render_latex
    """
    )

