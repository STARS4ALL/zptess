# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2021
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import logging

# -------------
# Local imports
# -------------

from zptool.utils import paging, section_read, section_display, update_property

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("zptool")

# ====================
# 'reference' commands
# ====================

def update(connection, options):
    '''Updates reference section in config database'''
    if options.model is not None:
        update_property(connection,'reference','model',options.model)
    if options.name is not None:
        update_property(connection,'reference','name',options.name)
    if options.mac is not None:
        update_property(connection,'reference','mac',options.mac)
    if options.firmware is not None:
        update_property(connection,'reference','firmware',options.firmware)
    if options.zp is not None:
        update_property(connection,'reference','zp',options.zp)
    view(connection, options)


def view(connection, options):
    '''View reference section in config database'''
    cursor = section_read(connection, 'reference')
    section_display(cursor.fetchall())