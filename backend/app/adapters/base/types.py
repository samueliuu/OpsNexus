from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PowerState(str, Enum):
    ON = "on"
    OFF = "off"
    POWERING_ON = "powering_on"
    POWERING_OFF = "powering_off"
    REBOOT = "reboot"
    UNKNOWN = "unknown"


class PowerAction(str, Enum):
    ON = "on"
    OFF = "off"
    GRACEFUL_OFF = "graceful_off"
    FORCE_OFF = "force_off"
    RESTART = "restart"
    GRACEFUL_RESTART = "graceful_restart"
    FORCE_RESTART = "force_restart"
    NMI = "nmi"


class BMCStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    ERROR = "error"


class HealthStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class BMCConnection:
    host: str
    username: str
    password: str
    protocol: str = "redfish"
    port: int = 443
    verify_ssl: bool = False
    timeout: int = 30


@dataclass
class SystemInfo:
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    sku: str = ""
    bios_version: str = ""
    bmc_version: str = ""
    bmc_ip: str = ""
    hostname: str = ""
    power_state: PowerState = PowerState.UNKNOWN
    health: HealthStatus = HealthStatus.UNKNOWN
    processor_count: int = 0
    processor_model: str = ""
    memory_total_gb: float = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SensorData:
    name: str
    reading: Optional[float] = None
    unit: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    sensor_type: str = ""
    lower_threshold_critical: Optional[float] = None
    upper_threshold_critical: Optional[float] = None
    lower_threshold_fatal: Optional[float] = None
    upper_threshold_fatal: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SELEntry:
    record_id: int
    timestamp: str
    sensor_type: str
    sensor_name: str
    event_type: str
    severity: str
    description: str
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FirmwareInfo:
    component: str
    current_version: str = ""
    available_version: str = ""
    update_status: str = "up_to_date"
    component_id: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NetworkAdapter:
    id: str
    name: str = ""
    mac_address: str = ""
    ip_addresses: List[str] = field(default_factory=list)
    link_status: str = "unknown"
    speed_mbps: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StorageController:
    id: str
    name: str = ""
    model: str = ""
    firmware_version: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    drives: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PowerSupply:
    id: str
    name: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    input_watts: Optional[float] = None
    output_watts: Optional[float] = None
    capacity_watts: Optional[float] = None
    model: str = ""
    serial: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Fan:
    id: str
    name: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    reading_rpm: Optional[float] = None
    reading_percent: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryModule:
    id: str
    name: str = ""
    capacity_mb: int = 0
    speed_mhz: int = 0
    type: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    manufacturer: str = ""
    serial: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Processor:
    id: str
    name: str = ""
    model: str = ""
    cores: int = 0
    threads: int = 0
    speed_ghz: float = 0
    status: HealthStatus = HealthStatus.UNKNOWN
    raw_data: Dict[str, Any] = field(default_factory=dict)
