#!/usr/bin/env python
# coding=utf-8
"""
Robot Framework LDTP Library

LDTPLibrary is a gui application testing library for Robot Framework.

It uses the LDTP (Linux Desktop Test Project) libraries internally to control a gui application.
See http://ldtp.freedesktop.org/wiki/ for more information on LDTP.

@author: Wang Yang <wywincl@gmail.com>
@copyright: Copyright (c) 2015-2016 Wang Yang
@license: GPLv3

See 'LICENSE' in the source distribution for more information.
"""

from version import VERSION
from keywords import *

__version__ = VERSION


class LDTPLibrary(LDTPDynamicKeywords):
    """
    LDTPLibrary is a gui application testing library for Robot Framework.

    It uses the LDTP (Linux Desktop Test Project) libraries internally to control a gui application.
    See http://ldtp.freedesktop.org/wiki/ for more information on LDTP.

    Author: John.Wang <wywincl@gmail.com>

    Examples:

    |  *Settings*  |  *Value*  |
    |   Library    | LDTPLibrary |

    |  *Variables* |  *Value*  |
    |  ${APP_NAME} |  gnome-calculator |
    |  ${FRM_NAME} |  frmCalculator |

    |  *Test Cases*  |  *Action*  |  *Argument*  |  *Arguments*  |
    |  Example_Test  | Launch App | ${APP_NAME}  |               |
    |                | Click      | ${FRM_NAME}  |     btn1      |

    """

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'
    ROBOT_LIBRARY_VERSION = VERSION

    def __init__(self):
        for base in LDTPLibrary.__bases__:
            base.__init__(self)


