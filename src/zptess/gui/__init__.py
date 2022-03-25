# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os.path

# Access SQL scripts withing the package
from pkg_resources import resource_filename

#--------------
# local imports
# -------------

# ----------------
# Module constants
# ----------------

ICONS_DIR   = resource_filename(__name__, os.path.join('resources', 'img' ))
IMG_ROI     = resource_filename(__name__, os.path.join('resources', 'img', 'roi.png'))

# About Widget resources configuration
ABOUT_DESC_TXT = resource_filename(__name__, os.path.join('resources', 'about', 'descr.txt'))
ABOUT_ACK_TXT  = resource_filename(__name__, os.path.join('resources', 'about', 'ack.txt'))
ABOUT_IMG      = resource_filename(__name__, os.path.join('resources', 'about', 'esfera192.png'))
ABOUT_ICONS = (
	('Universidad Complutense de Madrid', resource_filename(__name__, os.path.join('resources', 'about', 'ucm64.png'))),
	('GUAIX', resource_filename(__name__, os.path.join('resources', 'about', 'guaix60.jpg'))),
	('ACTION PROJECT EU', resource_filename(__name__, os.path.join('resources', 'about', 'action64.png'))),
)


# -----------------------
# Module global variables
# -----------------------
