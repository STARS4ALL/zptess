# ---------------------------
# Third-party library imports
# ----------------------------

from sqlalchemy import select
from zptessdao.asyncio import Config

# --------------
# local imports
# -------------

from ..dao import Session

async def load_config(session: Session, section: str, prop: str) -> str | None:
    q = select(Config.value).where(Config.section == section, Config.prop == prop)
    return (await session.scalars(q)).one_or_none()