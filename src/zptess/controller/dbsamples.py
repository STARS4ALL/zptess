# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import logging


from datetime import datetime

# ---------------------------
# Third-party library imports
# ----------------------------

from sqlalchemy import select
from lica.asyncio.photometer import Role
from zptessdao.asyncio import SampleView

# --------------
# local imports
# -------------

from ..dao import Session
from ..constants import FreqSequence, TimeSequence, NameSequence

# -----------------------
# Module global variables
# -----------------------

# get the module logger
log = logging.getLogger(__name__.split(".")[-1])


# ------------------
# Auxiliar functions
# ------------------


class Controller:
    def __init__(self):
        pass

    async def samples(self, session_id: datetime, role: Role) -> tuple[FreqSequence, TimeSequence, NameSequence]:
        """Used by the persistent controller"""
        log.info("fetching samples from session %s", session_id)
        async with Session() as session:
            async with session.begin():
                q = (
                    select(SampleView.freq, SampleView.tstamp, SampleView.name).distinct()
                    .where(SampleView.session == session_id, SampleView.role == role)
                )
                samples = (await session.execute(q)).all()
                log.info("found %d %s samples", len(samples), role)
                return zip(*samples)

