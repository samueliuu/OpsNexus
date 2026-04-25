from abc import ABC, abstractmethod
from typing import List

from app.adapters.base.types import (
    BMCConnection,
    Fan,
    FirmwareInfo,
    MemoryModule,
    NetworkAdapter,
    PowerAction,
    PowerState,
    PowerSupply,
    Processor,
    SELEntry,
    SensorData,
    StorageController,
    SystemInfo,
)


class ServerAdapter(ABC):
    """Abstract base class for server brand adapters."""

    brand: str = ""
    supported_models: List[str] = []

    def __init__(self, connection: BMCConnection):
        self.connection = connection
        self._client = None

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to BMC."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to BMC."""
        pass

    @abstractmethod
    async def get_system_info(self) -> SystemInfo:
        """Get server system information."""
        pass

    @abstractmethod
    async def get_power_state(self) -> PowerState:
        """Get current power state."""
        pass

    @abstractmethod
    async def set_power_action(self, action: PowerAction) -> PowerState:
        """Execute power action."""
        pass

    @abstractmethod
    async def get_sensor_data(self) -> List[SensorData]:
        """Get sensor readings (temperature, voltage, fan speed, etc.)."""
        pass

    @abstractmethod
    async def get_sel_logs(self, limit: int = 100) -> List[SELEntry]:
        """Get System Event Log entries."""
        pass

    @abstractmethod
    async def get_firmware_inventory(self) -> List[FirmwareInfo]:
        """Get firmware inventory."""
        pass

    @abstractmethod
    async def get_network_adapters(self) -> List[NetworkAdapter]:
        """Get network adapter information."""
        pass

    @abstractmethod
    async def get_storage_controllers(self) -> List[StorageController]:
        """Get storage controller information."""
        pass

    @abstractmethod
    async def get_power_supplies(self) -> List[PowerSupply]:
        """Get power supply information."""
        pass

    @abstractmethod
    async def get_fans(self) -> List[Fan]:
        """Get fan information."""
        pass

    @abstractmethod
    async def get_memory(self) -> List[MemoryModule]:
        """Get memory module information."""
        pass

    @abstractmethod
    async def get_processors(self) -> List[Processor]:
        """Get processor information."""
        pass

    async def health_check(self) -> bool:
        """Check if BMC is reachable."""
        try:
            await self.connect()
            await self.get_power_state()
            return True
        except Exception:
            return False
        finally:
            await self.disconnect()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
