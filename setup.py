import os
import os.path
import sys
import subprocess

from setuptools import setup, Extension
import versioneer

# Default description in markdown
long_description = open('README.md').read()
 
# Converts from makrdown to rst using pandoc
# and its python binding.
# Docunetation is uploaded in PyPi when registering
# by issuing `python setup.py register`

# try:
#     import subprocess
#     import pandoc
 
# except:
#     print("ERROR: pandoc is necessary to package this utility")
#     sys.exit(1)

# try:
 
#     process = subprocess.Popen(
#         ['which pandoc'],
#         shell=True,
#         stdout=subprocess.PIPE,
#         universal_newlines=True
#     )
 
#     pandoc_path = process.communicate()[0]
#     pandoc_path = pandoc_path.strip('\n')
 
#     pandoc.core.PANDOC_PATH = pandoc_path
 
#     doc = pandoc.Document()
#     doc.markdown = long_description
 
#     long_description = doc.rst
 
# except:
#     print("ERROR generating documentation with pandoc")
#     sys.exit(1)
   

PKG_NAME     = 'zptess'
AUTHOR       = 'Rafael Gonzalez'
AUTHOR_EMAIL = 'astrorafael@gmail.es'
DESCRIPTION  = 'Utility to calibrate TESS-W photometers',
LICENSE      = 'MIT'
KEYWORDS     = 'Astronomy Python RaspberryPi'
URL          = 'http://github.com/astrorafael/tessdb/'
PACKAGES     = ["zptess","zptess.service"]
DEPENDENCIES = [
                  'pyserial',
                  'requests',
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
    'Operating System :: Windows',
    'Programming Language :: Python :: 2.7',
    'Topic :: Scientific/Engineering :: Astronomy',
    'Topic :: Scientific/Engineering :: Atmospheric Science',
    'Development Status :: 4 - Beta',
]




if os.name == "posix":
  import shlex
    
  DATA_FILES  = [ 
    ('/etc/zptess',      ['files/etc/zptess/config.example.ini',]),
    ('/usr/local/bin',   ['files/usr/local/bin/zptess']),
  ]
  
  # Some fixes before setup
  if not os.path.exists("/var/zptess"):
    print("creating directory /var/zptess")
    args = shlex.split( "mkdir /var/zptess")
    subprocess.call(args)

elif os.name == "nt":

  DATA_FILES  = [ 
    (r'C:\zptess',        [r'files\etc\zptess\config.example.ini', r'files\winnt\zptess.bat']),
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
          long_description = long_description,
          license          = LICENSE,
          keywords         = KEYWORDS,
          url              = URL,
          classifiers      = CLASSIFIERS,
          packages         = PACKAGES,
          install_requires = DEPENDENCIES,
          data_files       = DATA_FILES
      )

