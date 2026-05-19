from .alice import alice
from .sam import sam

AGENTS = {a.name: a for a in (alice, sam)}
