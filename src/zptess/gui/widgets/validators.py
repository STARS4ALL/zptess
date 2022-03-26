# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import re

#--------------
# local imports
# -------------

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

# -----------------------
# Module global functions
# -----------------------


def float_validator(new_val):
    try:
        float(new_val)
    except ValueError:
        return False
    else:
        return True

def ip_validator(ip):
    '''Validate an IPv4 address returning True or False'''
    return [ 0 <= int(x) < 256 for x in re.split(r'\.', re.match(r'^\d+\.\d+\.\d+\.\d+$',ip).group(0))].count(True) == 4


def mac_validator(mac):
    '''Validate a MAC address (case insensitive'''
    p = re.compile(r'^([0-9a-f]{2}(?::[0-9a-f]{2}){5})$', re.IGNORECASE)
    matchobj = re.search(p, mac)
    if re.search(p, mac):
        result = True
    else:
        result = False
    return result

def ip_validator(ip):
    '''Validate an IPv4 address returning True or False'''
    p = re.compile(r'^([0-9]{1,3}(?:\.[0-9]{1,3}){3})$', re.IGNORECASE)
    matchobj = re.search(p, ip)
    if re.search(p, ip):
        result = True
    else:
        result = False
    return result