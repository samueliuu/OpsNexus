from app.adapters.base import (
    AdapterRegistry,
    BMCConnection,
    PowerAction,
    PowerState,
    ServerAdapter,
    register_adapter,
)

# Import all adapters to trigger registration
from app.adapters.dell import DellAdapter
from app.adapters.h3c import H3CAdapter
from app.adapters.hpe import HPEAdapter
from app.adapters.huawei import HuaweiAdapter
from app.adapters.inspur import InspurAdapter
from app.adapters.lenovo import LenovoAdapter
from app.adapters.sugon import SugonAdapter
from app.adapters.xfusion import XFusionAdapter

__all__ = [
    "AdapterRegistry",
    "BMCConnection",
    "DellAdapter",
    "HPEAdapter",
    "LenovoAdapter",
    "HuaweiAdapter",
    "InspurAdapter",
    "H3CAdapter",
    "SugonAdapter",
    "XFusionAdapter",
    "PowerAction",
    "PowerState",
    "ServerAdapter",
    "register_adapter",
]
