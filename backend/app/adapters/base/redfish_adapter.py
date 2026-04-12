from typing import Any, Dict, List, Optional

from app.adapters.base.adapter import ServerAdapter
from app.adapters.base.redfish import RedfishClient, REDFISH_POWER_ACTIONS, REDFISH_POWER_STATE_MAP
from app.adapters.base.types import (
    BMCConnection,
    Fan,
    FirmwareInfo,
    HealthStatus,
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
from app.core.exceptions import BMCConnectionException
from app.core.logging import get_logger

logger = get_logger(__name__)


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


class RedfishAdapter(ServerAdapter):
    """Generic Redfish adapter - base for all Redfish-compliant servers.

    Powered by DMTF python-redfish-library for session management
    with httpx AsyncClient for concurrent data retrieval.
    Resource IDs are cached on connect() to avoid repeated discovery.
    """

    brand: str = "generic"
    supported_models: List[str] = ["*"]

    def __init__(self, connection: BMCConnection):
        super().__init__(connection)
        self._redfish = RedfishClient(connection)
        self._system_id: Optional[str] = None
        self._chassis_id: Optional[str] = None
        self._manager_id: Optional[str] = None

    async def connect(self) -> None:
        await self._redfish.connect()
        await self._discover_ids()

    async def disconnect(self) -> None:
        await self._redfish.disconnect()

    async def _discover_ids(self) -> None:
        try:
            systems = await self._redfish.get("/redfish/v1/Systems")
            members = systems.get("Members", [])
            if members:
                odata_id = members[0].get("@odata.id", "")
                self._system_id = odata_id.rstrip("/").split("/")[-1]
        except BMCAuthenticationException:
            raise
        except Exception:
            pass

        try:
            chassis = await self._redfish.get("/redfish/v1/Chassis")
            members = chassis.get("Members", [])
            if members:
                odata_id = members[0].get("@odata.id", "")
                self._chassis_id = odata_id.rstrip("/").split("/")[-1]
        except BMCAuthenticationException:
            raise
        except Exception:
            pass

        try:
            managers = await self._redfish.get("/redfish/v1/Managers")
            members = managers.get("Members", [])
            if members:
                odata_id = members[0].get("@odata.id", "")
                self._manager_id = odata_id.rstrip("/").split("/")[-1]
        except BMCAuthenticationException:
            raise
        except Exception:
            pass

    @property
    def _system_path(self) -> str:
        return f"/redfish/v1/Systems/{self._system_id or '1'}"

    @property
    def _chassis_path(self) -> str:
        return f"/redfish/v1/Chassis/{self._chassis_id or '1'}"

    @property
    def _manager_path(self) -> str:
        return f"/redfish/v1/Managers/{self._manager_id or '1'}"

    async def _get_system_data(self) -> Dict[str, Any]:
        return await self._redfish.get(self._system_path)

    async def get_system_info(self) -> SystemInfo:
        data = await self._get_system_data()

        return SystemInfo(
            manufacturer=data.get("Manufacturer", ""),
            model=data.get("Model", ""),
            serial_number=data.get("SerialNumber", ""),
            sku=data.get("SKU", ""),
            bios_version=data.get("BiosVersion", ""),
            bmc_version="",
            bmc_ip=self.connection.host,
            hostname=data.get("HostName", ""),
            power_state=self._map_power_state(data.get("PowerState", "")),
            health=self._map_health(data.get("Status", {}).get("Health", "")),
            processor_count=data.get("ProcessorSummary", {}).get("Count", 0),
            processor_model=data.get("ProcessorSummary", {}).get("Model", ""),
            memory_total_gb=float(data.get("MemorySummary", {}).get("TotalSystemMemoryGiB", 0)),
            raw_data=data,
        )

    async def get_power_state(self) -> PowerState:
        data = await self._get_system_data()
        return self._map_power_state(data.get("PowerState", ""))

    async def set_power_action(self, action: PowerAction) -> PowerState:
        data = await self._get_system_data()

        actions = data.get("Actions", {})
        reset_action = actions.get("#ComputerSystem.Reset", {})
        reset_url = reset_action.get("target", f"{self._system_path}/Actions/ComputerSystem.Reset")

        redfish_action = REDFISH_POWER_ACTIONS.get(action.value, "On")
        await self._redfish.post(reset_url, {"ResetType": redfish_action})

        return await self.get_power_state()

    async def get_sensor_data(self) -> List[SensorData]:
        sensors = []

        try:
            thermal = await self._redfish.get(f"{self._chassis_path}/Thermal")
            for temp in thermal.get("Temperatures", []):
                sensors.append(SensorData(
                    name=temp.get("Name", ""),
                    reading=temp.get("ReadingCelsius"),
                    unit="Celsius",
                    status=self._map_health(temp.get("Status", {}).get("Health", "")),
                    sensor_type="Temperature",
                    upper_threshold_critical=temp.get("UpperThresholdCritical"),
                    lower_threshold_critical=temp.get("LowerThresholdCritical"),
                    raw_data=temp,
                ))

            for fan in thermal.get("Fans", []):
                sensors.append(SensorData(
                    name=fan.get("Name", ""),
                    reading=fan.get("Reading"),
                    unit=fan.get("ReadingUnits", "RPM"),
                    status=self._map_health(fan.get("Status", {}).get("Health", "")),
                    sensor_type="Fan",
                    lower_threshold_critical=fan.get("LowerThresholdCritical"),
                    upper_threshold_critical=fan.get("UpperThresholdCritical"),
                    raw_data=fan,
                ))
        except Exception as e:
            logger.warning(f"Failed to get thermal data: {e}")

        try:
            power = await self._redfish.get(f"{self._chassis_path}/Power")
            for voltage in power.get("Voltages", []):
                sensors.append(SensorData(
                    name=voltage.get("Name", ""),
                    reading=voltage.get("ReadingVolts"),
                    unit="Volts",
                    status=self._map_health(voltage.get("Status", {}).get("Health", "")),
                    sensor_type="Voltage",
                    lower_threshold_critical=voltage.get("LowerThresholdCritical"),
                    upper_threshold_critical=voltage.get("UpperThresholdCritical"),
                    raw_data=voltage,
                ))
        except Exception as e:
            logger.warning(f"Failed to get power data: {e}")

        return sensors

    async def get_sel_logs(self, limit: int = 100) -> List[SELEntry]:
        entries = []

        try:
            log_service = await self._redfish.get(f"{self._system_path}/LogServices/SEL")
            entries_url = log_service.get("Entries", {}).get("@odata.id", "")
            if not entries_url:
                entries_url = f"{self._system_path}/LogServices/SEL/Entries"

            log_data = await self._redfish.get(entries_url)
            members = log_data.get("Members", [])

            for entry in members[:limit]:
                entries.append(SELEntry(
                    record_id=_safe_int(entry.get("Id", "0")),
                    timestamp=entry.get("Created", ""),
                    sensor_type=entry.get("SensorType", ""),
                    sensor_name=str(entry.get("SensorNumber", "")),
                    event_type=entry.get("EventType", ""),
                    severity=self._map_severity(entry.get("Severity", "")),
                    description=entry.get("Message", ""),
                    raw_data=entry,
                ))
        except Exception as e:
            logger.warning(f"Failed to get SEL logs: {e}")

        return entries

    async def get_firmware_inventory(self) -> List[FirmwareInfo]:
        firmware_list = []

        try:
            inventory = await self._redfish.get("/redfish/v1/UpdateService/FirmwareInventory")
            for member in inventory.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        fw_data = await self._redfish.get(url)
                        firmware_list.append(FirmwareInfo(
                            component=fw_data.get("Name", ""),
                            current_version=fw_data.get("Version", ""),
                            update_status=self._map_update_status(fw_data),
                            component_id=fw_data.get("Id", ""),
                            raw_data=fw_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get firmware inventory: {e}")

        return firmware_list

    async def get_network_adapters(self) -> List[NetworkAdapter]:
        adapters = []

        try:
            nics = await self._redfish.get(f"{self._system_path}/EthernetInterfaces")
            for member in nics.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        nic_data = await self._redfish.get(url)
                        ip_addresses = []
                        for ipv4 in nic_data.get("IPv4Addresses", []):
                            addr = ipv4.get("Address", "")
                            if addr:
                                ip_addresses.append(addr)

                        adapters.append(NetworkAdapter(
                            id=nic_data.get("Id", ""),
                            name=nic_data.get("Name", ""),
                            mac_address=nic_data.get("MACAddress", ""),
                            ip_addresses=ip_addresses,
                            link_status=nic_data.get("LinkStatus", "unknown"),
                            speed_mbps=nic_data.get("SpeedMbps", 0),
                            raw_data=nic_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get network adapters: {e}")

        return adapters

    async def get_storage_controllers(self) -> List[StorageController]:
        controllers = []

        try:
            storage = await self._redfish.get(f"{self._system_path}/Storage")
            for member in storage.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        ctrl_data = await self._redfish.get(url)
                        controllers.append(StorageController(
                            id=ctrl_data.get("Id", ""),
                            name=ctrl_data.get("Name", ""),
                            model="",
                            status=self._map_health(
                                ctrl_data.get("Status", {}).get("Health", "")
                            ),
                            raw_data=ctrl_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get storage controllers: {e}")

        return controllers

    async def get_power_supplies(self) -> List[PowerSupply]:
        supplies = []

        try:
            power = await self._redfish.get(f"{self._chassis_path}/Power")
            for ps_data in power.get("PowerSupplies", []):
                supplies.append(PowerSupply(
                    id=ps_data.get("Id", ""),
                    name=ps_data.get("Name", ""),
                    status=self._map_health(ps_data.get("Status", {}).get("Health", "")),
                    input_watts=ps_data.get("PowerInputWatts"),
                    output_watts=ps_data.get("LastPowerOutputWatts"),
                    capacity_watts=ps_data.get("PowerCapacityWatts"),
                    model=ps_data.get("Model", ""),
                    serial=ps_data.get("SerialNumber", ""),
                    raw_data=ps_data,
                ))
        except Exception as e:
            logger.warning(f"Failed to get power supplies: {e}")

        return supplies

    async def get_fans(self) -> List[Fan]:
        fans = []

        try:
            thermal = await self._redfish.get(f"{self._chassis_path}/Thermal")
            for fan_data in thermal.get("Fans", []):
                reading = fan_data.get("Reading")
                reading_units = fan_data.get("ReadingUnits", "RPM")

                fans.append(Fan(
                    id=fan_data.get("Id", fan_data.get("Name", "")),
                    name=fan_data.get("Name", ""),
                    status=self._map_health(fan_data.get("Status", {}).get("Health", "")),
                    reading_rpm=reading if "RPM" in reading_units else None,
                    reading_percent=reading if "Percent" in reading_units else None,
                    raw_data=fan_data,
                ))
        except Exception as e:
            logger.warning(f"Failed to get fans: {e}")

        return fans

    async def get_memory(self) -> List[MemoryModule]:
        modules = []

        try:
            memory = await self._redfish.get(f"{self._system_path}/Memory")
            for member in memory.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        mem_data = await self._redfish.get(url)
                        modules.append(MemoryModule(
                            id=mem_data.get("Id", ""),
                            name=mem_data.get("Name", ""),
                            capacity_mb=mem_data.get("CapacityMiB", 0),
                            speed_mhz=mem_data.get("OperatingSpeedMhz", 0),
                            type=mem_data.get("MemoryDeviceType", ""),
                            status=self._map_health(
                                mem_data.get("Status", {}).get("Health", "")
                            ),
                            manufacturer=mem_data.get("Manufacturer", ""),
                            serial=mem_data.get("SerialNumber", ""),
                            raw_data=mem_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get memory: {e}")

        return modules

    async def get_processors(self) -> List[Processor]:
        processors = []

        try:
            proc_collection = await self._redfish.get(f"{self._system_path}/Processors")
            for member in proc_collection.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        proc_data = await self._redfish.get(url)
                        processors.append(Processor(
                            id=proc_data.get("Id", ""),
                            name=proc_data.get("Name", ""),
                            model=proc_data.get("Model", ""),
                            cores=proc_data.get("TotalCores", 0),
                            threads=proc_data.get("TotalThreads", 0),
                            speed_ghz=(proc_data.get("MaxSpeedMHz") or 0) / 1000.0,
                            status=self._map_health(
                                proc_data.get("Status", {}).get("Health", "")
                            ),
                            raw_data=proc_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get processors: {e}")

        return processors

    @staticmethod
    def _map_power_state(redfish_state: str) -> PowerState:
        mapped = REDFISH_POWER_STATE_MAP.get(redfish_state, "unknown")
        return PowerState(mapped)

    @staticmethod
    def _map_health(health: str) -> HealthStatus:
        mapping = {
            "OK": HealthStatus.OK,
            "Warning": HealthStatus.WARNING,
            "Critical": HealthStatus.CRITICAL,
        }
        return mapping.get(health, HealthStatus.UNKNOWN)

    @staticmethod
    def _map_severity(severity: str) -> str:
        mapping = {
            "OK": "info",
            "Warning": "warning",
            "Critical": "critical",
        }
        return mapping.get(severity, "info")

    @staticmethod
    def _map_update_status(data: Dict[str, Any]) -> str:
        status = data.get("Status", {}).get("Health", "")
        if status == "OK":
            return "up_to_date"
        elif status == "Warning":
            return "update_available"
        elif status == "Critical":
            return "failed"
        return "up_to_date"
