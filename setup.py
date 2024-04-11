import distutils
import glob
import os
from distutils.core import setup

try:
    from pip import main as pipmain
except:
    from pip._internal import main as pipmain
pipmain(['install', 'appdirs'])

def read_version(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read().strip()
    except FileNotFoundError:
        return '0.0.0'


__version__ = read_version(os.path.join('src', 'pyrap', '.version'))

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


# def datafiles(d):
#     data_files = []
#     for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), d)):
#         if not files: continue
#         root_ = root.replace(os.getcwd() + os.path.sep, '')
#         data_files.append((root_, [os.path.join(root_, f) for f in files]))
#     return data_files


def datapath():
    '''Returns the path where app data is to be installed.'''
    import appdirs
    if iamroot():
        return appdirs.site_data_dir(appname, appauthor)
    else:
        return appdirs.user_data_dir(appname, appauthor)


_ROOT = os.path.abspath(os.path.dirname(__file__))
def get_data(path):
    return os.path.join('data', path)

#
# def files(path):
#     for file in os.listdir(path):
#         if os.path.isfile(os.path.join(path, file)):
#             yield file
#
# def package_files(pdirs):
#     data_files = []
#     directories = glob.glob(f'{pdirs}/*/', recursive=True)
#     print("FOUND", directories)
#     for directory in directories:
#         files = glob.glob(directory+'*', recursive=True)
#         print("FOUND FILES", files)
#         files =  [f for f in files if os.path.isfile(f)]
#         data_files.append((directory, files))
#     print("================================================DATAFILES", data_files)
#     return data_files

def f():
    print("FILES: ", glob.glob(f"{os.path.join('pyrap', 'data')}/*/"))
    return glob.glob(f"{os.path.join('pyrap', 'data')}/*/")

# extra_files = package_files(os.path.join('pyrap', 'data'))
data_files = f()


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
              'pyrap.pwt',
              'pyrap.pwt.audio',
              'pyrap.pwt.barchart',
              'pyrap.pwt.bubblyclusters',
              'pyrap.pwt.d3widget',
              'pyrap.pwt.graph',
              'pyrap.pwt.heatmap',
              'pyrap.pwt.plot',
              'pyrap.pwt.radar',
              'pyrap.pwt.radar_smoothed',
              'pyrap.pwt.radialdendrogramm',
              'pyrap.pwt.radialtree',
              'pyrap.pwt.ros3d',
              'pyrap.pwt.svg',
              'pyrap.pwt.tol',
              'pyrap.pwt.tree',
              'pyrap.pwt.video',
              'pyrap.web',
              'pyrap.web.contrib',
              'pyrap.web.wsgiserver'
              ],
    package_dir={'': 'src'},
    version=__version__,
    install_requires=requirements(),
    long_description=read('README'),
    package_data={'pyrap': ['data/3rdparty/d3/*',
                            'data/css/fonts/*',
                            'data/css/*',
                            'data/etc/*',
                            'data/html/*',
                            'data/js/*',
                            'data/js/rwt/**/*',
                            'data/resource/**/**/*',
                            '.version']
                  },
    # data_files=extra_files,
    # data_files=[ ("pyrap",  data_files)],
    include_package_data=True,
    description='pyRAP is a framework for implementing extremely powerful and beautiful web-based AJAX '
                'applications in pure Python. No HTML. No JavaScript. No PHP. Just pure Python. It has been designed '
                'as a lightweight, easy-to-use yet powerful library that makes development of SaaS applications as '
                'easy and fast as possible.',
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
    entry_points={
        'console_scripts': [
            'controls=pyrap_examples.controls.pyrap_controls:main',
            'helloworld=pyrap_examples.helloworld.main:main',
            'layouts=pyrap_examples.layouts.gridlayout:main',
            'admin=pyrap_examples.pyrap_admin.admin:main',
            'sayhello=pyrap_examples.sayhello.main:main'
        ],
    },
    # cmdclass={'install': myinstall}
)
