import os
import os.path
import sys

from setuptools import setup, Extension
import versioneer

# Default description in markdown
#long_description = open('README.md').read()
 
# Converts from makrdown to rst using pandoc
# and its python binding.
# Docunetation is uploaded in PyPi when registering
# by issuing `python setup.py register`

LONG_DESCRIPTION = open('README.md').read()
PKG_NAME     = 'zptess'
AUTHOR       = 'Rafael Gonzalez'
AUTHOR_EMAIL = 'astrorafael@gmail.es'
DESCRIPTION  = 'Utility to calibrate TESS-W photometers',
LICENSE      = 'MIT'
KEYWORDS     = 'Astronomy Python RaspberryPi'
URL          = 'http://github.com/astrorafael/tessdb/'
PACKAGES     = ["zptess"]
DEPENDENCIES = [
                  'pyserial',
                  'treq',
                  'twisted >= 16.3.0',
                ]

if sys.version_info[0] == 2:
  DEPENDENCIES.append('statistics')

CLASSIFIERS  = [
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 2.7',
    'Topic :: Scientific/Engineering :: Astronomy',
    'Topic :: Scientific/Engineering :: Atmospheric Science',
    'Development Status :: 4 - Beta',
]

if os.name == "posix":
  DATA_FILES  = [ 
    ('/etc/zptess',      ['files/etc/zptess/config.example.ini',]),
    ('/usr/local/bin',   ['files/usr/local/bin/zptessw',
                          'files/usr/local/bin/zptessp',
                          'files/usr/local/bin/zptas',]),
   ]
else:
  print("ERROR: unsupported OS {name}".format(name = os.name))
  sys.exit(1)

                                
setup(name                  = PKG_NAME,
          version          = versioneer.get_version(),
          cmdclass         = versioneer.get_cmdclass(),
          author           = AUTHOR,
          author_email     = AUTHOR_EMAIL,
          description      = DESCRIPTION,
          long_description = LONG_DESCRIPTION,
          long_description_content_type = "text/markdown",
          license          = LICENSE,
          keywords         = KEYWORDS,
          url              = URL,
          classifiers      = CLASSIFIERS,
          packages         = PACKAGES,
          install_requires = DEPENDENCIES,
          data_files       = DATA_FILES
      )

