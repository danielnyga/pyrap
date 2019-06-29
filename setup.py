import distutils
import os
from distutils.core import setup

import _version
try:
    from pip import main as pipmain
except:
    from pip._internal import main as pipmain
pipmain(['install', 'appdirs'])

__version__ = _version.__version__
appname = _version.APPNAME
appauthor = _version.APPAUTHOR


def iamroot():
    '''Checks if this process has admin permissions.'''
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def requirements():
    with open('requirements.txt', 'r') as f:
        return [l.strip() for l in f.readlines() if l.strip()]


def datafiles(d):
    data_files = []
    for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), d)):
        if not files: continue
        root_ = root.replace(os.getcwd() + os.path.sep, '')
        data_files.append((root_, [os.path.join(root_, f) for f in files]))
    return data_files


def datapath():
    '''Returns the path where app data is to be installed.'''
    import appdirs
    if iamroot():
        return appdirs.site_data_dir(appname, appauthor)
    else:
        return appdirs.user_data_dir(appname, appauthor)


class myinstall(distutils.command.install.install):

    def __init__(self, *args, **kwargs):
        distutils.command.install.install.__init__(self, *args, **kwargs)
        self.distribution.get_command_obj('install_data').install_dir = datapath()

setup(
    name='pyrap-web',
    packages=['pyrap_examples',
              'pyrap_examples.controls',
              'pyrap_examples.helloworld',
              'pyrap_examples.layouts',
              'pyrap_examples.pyrap_admin',
              'pyrap_examples.sayhello',
              'pyrap',
              'pyrap._version',
              'pyrap.pwt',
              'pyrap.pwt.barchart',
              'pyrap.pwt.bubblyclusters',
              'pyrap.pwt.graph',
              'pyrap.pwt.plot',
              'pyrap.pwt.radar',
              'pyrap.pwt.radar_smoothed',
              'pyrap.pwt.radialdendrogramm',
              'pyrap.pwt.ros3d',
              'pyrap.pwt.svg',
              'pyrap.pwt.tree',
              'pyrap.pwt.video',
              'pyrap.web',
              'pyrap.web.contrib',
              'pyrap.web.wsgiserver'
              ],
    py_modules=[],
    package_dir={
        'pyrap': 'pyrap',
        'pyrap._version': '_version',
        '': '.'
    },
    package_data={'': ['*']},
    data_files=datafiles('3rdparty') +
               datafiles('css') +
               datafiles('etc') +
               datafiles('html') +
               datafiles('js') +
               datafiles('resource'),
    version=__version__,
    description='pyRAP is a framework for implementing extremely powerful and beautiful web-based AJAX '
                'applications in pure Python. No HTML. No JavaScript. No PHP. Just pure Python. It has been designed '
                'as a lightweight, easy-to-use yet powerful library that makes development of SaaS applications as '
                'easy and fast as possible.',
    long_description=read('README'),
    author='Daniel Nyga, Mareike Picklum',
    author_email='nyga@cs.uni-bremen.de, mareikep@cs.uni-bremen.de',
    url='https://pyrap.org/',
    download_url='https://github.com/danielnyga/pyrap/archive/{}.tar.gz'.format(__version__),
    keywords=['AJAX applications', 'python', 'web development'],
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Artificial Intelligence ',
        'Topic :: Software Development :: Widget Sets',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
    ],
    install_requires=requirements(),
    entry_points={
        'console_scripts': [
            'controls=pyrap_examples.controls.pyrap_controls:main',
            'helloworld=pyrap_examples.helloworld.main:main',
            'layouts=pyrap_examples.layouts.gridlayout:main',
            'admin=pyrap_examples.pyrap_admin.admin:main',
            'sayhello=pyrap_examples.sayhello.main:main'
        ],
    },
    cmdclass={'install': myinstall}
)
