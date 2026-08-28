"""DR.Xmail — Agents Mail: per-agent email platform for AI agents."""
from .mailbox import AgentMailbox
from . import store
from . import senders
from . import bus
from . import fedimail
from . import fedinode
from .fedimailbox import FederatedAgent
from . import bridge

__all__ = ["AgentMailbox", "store", "senders", "bus", "fedimail", "fedinode",
           "FederatedAgent", "bridge"]
