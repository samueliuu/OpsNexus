from typing import Any, Dict, List, Optional

from app.adapters.base.adapter import ServerAdapter
from app.adapters.base.redfish import RedfishClient
from app.adapters.base.registry import register_adapter
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
from app.core.logging import get_logger

logger = get_logger(__name__)

DELL_IDRAC_SYSTEM_ID = "System.Embedded.1"
DELL_IDRAC_CHASSIS_ID = "Chassis.Embedded.1"
DELL_IDRAC_MANAGER_ID = "iDRAC.Embedded.1"


@register_adapter("dell")
class DellAdapter(ServerAdapter):
    """Dell server adapter using iDRAC Redfish API.

    References: Dell iDRAC-Redfish-Scripting (github.com/dell/iDRAC-Redfish-Scripting)
    Dell iDRAC 9+ fully supports Redfish API with Dell-specific extensions:
    - iDRAC-specific OEM data under Dell namespace
    - Lifecycle Controller (LC) for firmware updates
    - iDRAC job queue for async operations
    - Dell OpenManage integration
    - RAID configuration via Dell OEM extensions
    - BIOS configuration via Dell OEM extensions
    """

    brand: str = "dell"
    supported_models: List[str] = [
        "PowerEdge R640", "PowerEdge R650", "PowerEdge R660",
        "PowerEdge R740", "PowerEdge R750", "PowerEdge R760",
        "PowerEdge R940", "PowerEdge R950",
        "PowerEdge T440", "PowerEdge T550", "PowerEdge T640",
        "PowerEdge C6420", "PowerEdge C6525",
        "PowerEdge XR4000", "PowerEdge XR5610",
    ]

    def __init__(self, connection: BMCConnection):
        super().__init__(connection)
        self._redfish = RedfishClient(connection)
        self._system_id: Optional[str] = None
        self._chassis_id: Optional[str] = None
        self._manager_id: Optional[str] = None

    async def connect(self) -> None:
        await self._redfish.connect()
        await self._discover_dell_ids()

    async def disconnect(self) -> None:
        await self._redfish.disconnect()

    async def _discover_dell_ids(self) -> None:
        try:
            systems = await self._redfish.get("/redfish/v1/Systems")
            for member in systems.get("Members", []):
                url = member.get("@odata.id", "")
                if "System.Embedded" in url or not self._system_id:
                    self._system_id = url.rstrip("/").split("/")[-1]
        except Exception:
            self._system_id = DELL_IDRAC_SYSTEM_ID

        try:
            chassis = await self._redfish.get("/redfish/v1/Chassis")
            for member in chassis.get("Members", []):
                url = member.get("@odata.id", "")
                if "Chassis.Embedded" in url or not self._chassis_id:
                    self._chassis_id = url.rstrip("/").split("/")[-1]
        except Exception:
            self._chassis_id = DELL_IDRAC_CHASSIS_ID

        try:
            managers = await self._redfish.get("/redfish/v1/Managers")
            for member in managers.get("Members", []):
                url = member.get("@odata.id", "")
                if "iDRAC" in url or not self._manager_id:
                    self._manager_id = url.rstrip("/").split("/")[-1]
        except Exception:
            self._manager_id = DELL_IDRAC_MANAGER_ID

    @property
    def _system_path(self) -> str:
        return f"/redfish/v1/Systems/{self._system_id or DELL_IDRAC_SYSTEM_ID}"

    @property
    def _chassis_path(self) -> str:
        return f"/redfish/v1/Chassis/{self._chassis_id or DELL_IDRAC_CHASSIS_ID}"

    @property
    def _manager_path(self) -> str:
        return f"/redfish/v1/Managers/{self._manager_id or DELL_IDRAC_MANAGER_ID}"

    async def _get_system_data(self) -> Dict[str, Any]:
        return await self._redfish.get(self._system_path)

    async def get_system_info(self) -> SystemInfo:
        data = await self._get_system_data()

        power_state_map = {
            "On": PowerState.ON, "Off": PowerState.OFF,
            "PoweringOn": PowerState.POWERING_ON, "PoweringOff": PowerState.POWERING_OFF,
        }
        health_map = {"OK": HealthStatus.OK, "Warning": HealthStatus.WARNING, "Critical": HealthStatus.CRITICAL}

        info = SystemInfo(
            manufacturer=data.get("Manufacturer", ""),
            model=data.get("Model", ""),
            serial_number=data.get("SerialNumber", ""),
            sku=data.get("SKU", ""),
            bios_version=data.get("BiosVersion", ""),
            bmc_version="",
            bmc_ip=self.connection.host,
            hostname=data.get("HostName", ""),
            power_state=power_state_map.get(data.get("PowerState", ""), PowerState.UNKNOWN),
            health=health_map.get(data.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
            processor_count=data.get("ProcessorSummary", {}).get("Count", 0),
            processor_model=data.get("ProcessorSummary", {}).get("Model", ""),
            memory_total_gb=data.get("MemorySummary", {}).get("TotalSystemMemoryGiB", 0),
            raw_data=data,
        )

        try:
            oem = data.get("Oem", {})
            dell_oem = oem.get("Dell", {})
            if dell_oem:
                dell_system = dell_oem.get("DellSystem", {})
                info.bmc_version = dell_system.get("iDRACVersion", "")
                info.raw_data["dell_oem"] = dell_oem
        except Exception as e:
            logger.debug(f"Failed to get Dell OEM data: {e}")

        try:
            manager = await self._redfish.get(self._manager_path)
            info.bmc_version = manager.get("FirmwareVersion", info.bmc_version)
            info.raw_data["manager"] = manager
        except Exception as e:
            logger.debug(f"Failed to get iDRAC manager data: {e}")

        return info

    async def get_power_state(self) -> PowerState:
        data = await self._get_system_data()
        power_map = {"On": PowerState.ON, "Off": PowerState.OFF,
                     "PoweringOn": PowerState.POWERING_ON, "PoweringOff": PowerState.POWERING_OFF}
        return power_map.get(data.get("PowerState", ""), PowerState.UNKNOWN)

    async def set_power_action(self, action: PowerAction) -> PowerState:
        data = await self._get_system_data()
        action_map = {
            PowerAction.ON: "On", PowerAction.OFF: "ForceOff",
            PowerAction.GRACEFUL_OFF: "GracefulShutdown", PowerAction.FORCE_OFF: "ForceOff",
            PowerAction.RESTART: "ForceRestart", PowerAction.GRACEFUL_RESTART: "GracefulRestart",
            PowerAction.FORCE_RESTART: "ForceRestart", PowerAction.NMI: "Nmi",
        }

        actions = data.get("Actions", {})
        reset_action = actions.get("#ComputerSystem.Reset", {})
        reset_url = reset_action.get("target", f"{self._system_path}/Actions/ComputerSystem.Reset")

        redfish_action = action_map.get(action, "On")
        await self._redfish.post(reset_url, {"ResetType": redfish_action})
        return await self.get_power_state()

    async def get_sensor_data(self) -> List[SensorData]:
        sensors = []
        health_map = {"OK": HealthStatus.OK, "Warning": HealthStatus.WARNING, "Critical": HealthStatus.CRITICAL}

        try:
            thermal = await self._redfish.get(f"{self._chassis_path}/Thermal")
            for temp in thermal.get("Temperatures", []):
                sensors.append(SensorData(
                    name=temp.get("Name", ""), reading=temp.get("ReadingCelsius"),
                    unit="Celsius", status=health_map.get(temp.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
                    sensor_type="Temperature", upper_threshold_critical=temp.get("UpperThresholdCritical"),
                    lower_threshold_critical=temp.get("LowerThresholdCritical"), raw_data=temp,
                ))
            for fan in thermal.get("Fans", []):
                sensors.append(SensorData(
                    name=fan.get("Name", ""), reading=fan.get("Reading"),
                    unit=fan.get("ReadingUnits", "RPM"), status=health_map.get(fan.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
                    sensor_type="Fan", lower_threshold_critical=fan.get("LowerThresholdCritical"),
                    upper_threshold_critical=fan.get("UpperThresholdCritical"), raw_data=fan,
                ))
        except Exception as e:
            logger.warning(f"Failed to get Dell thermal data: {e}")

        try:
            power = await self._redfish.get(f"{self._chassis_path}/Power")
            for voltage in power.get("Voltages", []):
                sensors.append(SensorData(
                    name=voltage.get("Name", ""), reading=voltage.get("ReadingVolts"),
                    unit="Volts", status=health_map.get(voltage.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
                    sensor_type="Voltage", lower_threshold_critical=voltage.get("LowerThresholdCritical"),
                    upper_threshold_critical=voltage.get("UpperThresholdCritical"), raw_data=voltage,
                ))
        except Exception as e:
            logger.warning(f"Failed to get Dell power data: {e}")

        return sensors

    async def get_sel_logs(self, limit: int = 100) -> List[SELEntry]:
        entries = []
        severity_map = {"OK": "info", "Warning": "warning", "Critical": "critical"}

        log_urls = [
            f"{self._manager_path}/LogServices/Lclog/Entries",
            f"{self._system_path}/LogServices/Sel/Entries",
        ]

        for log_url in log_urls:
            try:
                log_data = await self._redfish.get(log_url)
                for entry in log_data.get("Members", []):
                    message_id = entry.get("MessageId", "")
                    entries.append(SELEntry(
                        record_id=int(entry.get("Id", "0")),
                        timestamp=entry.get("Created", ""),
                        sensor_type=entry.get("SensorType", message_id.split(".")[-2] if "." in message_id else ""),
                        sensor_name=str(entry.get("SensorNumber", "")),
                        event_type=entry.get("EventType", ""),
                        severity=severity_map.get(entry.get("Severity", ""), "info"),
                        description=entry.get("Message", ""),
                        raw_data=entry,
                    ))
            except Exception as e:
                logger.debug(f"Failed to get Dell log from {log_url}: {e}")

        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:limit]

    async def get_firmware_inventory(self) -> List[FirmwareInfo]:
        firmware_list = []

        try:
            inventory = await self._redfish.get("/redfish/v1/UpdateService/FirmwareInventory")
            for member in inventory.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        fw_data = await self._redfish.get(url)
                        update_status = "up_to_date"
                        oem = fw_data.get("Oem", {})
                        dell_oem = oem.get("Dell", {})
                        available_version = dell_oem.get("AvailableVersion", "")
                        if dell_oem.get("UpdateStatus") == "Available":
                            update_status = "update_available"

                        firmware_list.append(FirmwareInfo(
                            component=fw_data.get("Name", ""),
                            current_version=fw_data.get("Version", ""),
                            available_version=available_version,
                            update_status=update_status,
                            component_id=fw_data.get("Id", ""),
                            raw_data=fw_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get Dell firmware inventory: {e}")

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
                        adapters.append(NetworkAdapter(
                            id=nic_data.get("Id", ""), name=nic_data.get("Name", ""),
                            mac_address=nic_data.get("MACAddress", ""),
                            link_status=nic_data.get("LinkStatus", "unknown"),
                            speed_mbps=nic_data.get("SpeedMbps", 0), raw_data=nic_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get Dell network adapters: {e}")
        return adapters

    async def get_storage_controllers(self) -> List[StorageController]:
        controllers = []
        health_map = {"OK": HealthStatus.OK, "Warning": HealthStatus.WARNING, "Critical": HealthStatus.CRITICAL}

        try:
            storage = await self._redfish.get(f"{self._system_path}/Storage")
            for member in storage.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        ctrl_data = await self._redfish.get(url)
                        drives = []
                        for drive_member in ctrl_data.get("Drives", []):
                            drive_url = drive_member.get("@odata.id", "")
                            if drive_url:
                                try:
                                    drive_data = await self._redfish.get(drive_url)
                                    drives.append({
                                        "id": drive_data.get("Id", ""), "name": drive_data.get("Name", ""),
                                        "model": drive_data.get("Model", ""), "capacity_bytes": drive_data.get("CapacityBytes", 0),
                                        "media_type": drive_data.get("MediaType", ""),
                                        "health": drive_data.get("Status", {}).get("Health", ""),
                                        "protocol": drive_data.get("Protocol", ""),
                                    })
                                except Exception:
                                    pass

                        model = ""
                        firmware = ""
                        storage_controllers = ctrl_data.get("StorageControllers", [])
                        if storage_controllers:
                            sc = storage_controllers[0]
                            model = sc.get("Model", "")
                            firmware = sc.get("FirmwareVersion", "")

                        controllers.append(StorageController(
                            id=ctrl_data.get("Id", ""), name=ctrl_data.get("Name", ""),
                            model=model, firmware_version=firmware,
                            status=health_map.get(ctrl_data.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
                            drives=drives, raw_data=ctrl_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get Dell storage controllers: {e}")
        return controllers

    async def get_power_supplies(self) -> List[PowerSupply]:
        supplies = []
        health_map = {"OK": HealthStatus.OK, "Warning": HealthStatus.WARNING, "Critical": HealthStatus.CRITICAL}

        try:
            power = await self._redfish.get(f"{self._chassis_path}/Power")
            for ps_data in power.get("PowerSupplies", []):
                supplies.append(PowerSupply(
                    id=ps_data.get("Id", ""), name=ps_data.get("Name", ""),
                    status=health_map.get(ps_data.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
                    input_watts=ps_data.get("PowerInputWatts"), output_watts=ps_data.get("LastPowerOutputWatts"),
                    capacity_watts=ps_data.get("PowerCapacityWatts"), model=ps_data.get("Model", ""),
                    serial=ps_data.get("SerialNumber", ""), raw_data=ps_data,
                ))
        except Exception as e:
            logger.warning(f"Failed to get Dell power supplies: {e}")
        return supplies

    async def get_fans(self) -> List[Fan]:
        fans = []
        health_map = {"OK": HealthStatus.OK, "Warning": HealthStatus.WARNING, "Critical": HealthStatus.CRITICAL}

        try:
            thermal = await self._redfish.get(f"{self._chassis_path}/Thermal")
            for fan_data in thermal.get("Fans", []):
                reading = fan_data.get("Reading")
                reading_units = fan_data.get("ReadingUnits", "RPM")
                fans.append(Fan(
                    id=fan_data.get("Id", fan_data.get("Name", "")), name=fan_data.get("Name", ""),
                    status=health_map.get(fan_data.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
                    reading_rpm=reading if "RPM" in reading_units else None,
                    reading_percent=reading if "Percent" in reading_units else None, raw_data=fan_data,
                ))
        except Exception as e:
            logger.warning(f"Failed to get Dell fans: {e}")
        return fans

    async def get_memory(self) -> List[MemoryModule]:
        modules = []
        health_map = {"OK": HealthStatus.OK, "Warning": HealthStatus.WARNING, "Critical": HealthStatus.CRITICAL}

        try:
            memory = await self._redfish.get(f"{self._system_path}/Memory")
            for member in memory.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        mem_data = await self._redfish.get(url)
                        modules.append(MemoryModule(
                            id=mem_data.get("Id", ""), name=mem_data.get("Name", ""),
                            capacity_mb=mem_data.get("CapacityMiB", 0), speed_mhz=mem_data.get("OperatingSpeedMhz", 0),
                            type=mem_data.get("MemoryDeviceType", ""),
                            status=health_map.get(mem_data.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
                            manufacturer=mem_data.get("Manufacturer", ""), serial=mem_data.get("SerialNumber", ""),
                            raw_data=mem_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get Dell memory: {e}")
        return modules

    async def get_processors(self) -> List[Processor]:
        processors = []
        health_map = {"OK": HealthStatus.OK, "Warning": HealthStatus.WARNING, "Critical": HealthStatus.CRITICAL}

        try:
            proc_collection = await self._redfish.get(f"{self._system_path}/Processors")
            for member in proc_collection.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        proc_data = await self._redfish.get(url)
                        processors.append(Processor(
                            id=proc_data.get("Id", ""), name=proc_data.get("Name", ""),
                            model=proc_data.get("Model", ""), cores=proc_data.get("TotalCores", 0),
                            threads=proc_data.get("TotalThreads", 0),
                            speed_ghz=(proc_data.get("MaxSpeedMHz") or 0) / 1000.0,
                            status=health_map.get(proc_data.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
                            raw_data=proc_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get Dell processors: {e}")
        return processors

    async def get_idrac_info(self) -> Dict[str, Any]:
        try:
            manager = await self._redfish.get(self._manager_path)
            oem = manager.get("Oem", {}).get("Dell", {})
            return {
                "firmware_version": manager.get("FirmwareVersion", ""),
                "model": manager.get("Model", ""),
                "status": manager.get("Status", {}).get("Health", ""),
                "ip_address": self.connection.host,
                "mac_address": manager.get("EthernetInterfaces", {}),
                "dell_oem": oem,
                "raw_data": manager,
            }
        except Exception as e:
            logger.warning(f"Failed to get iDRAC info: {e}")
            return {}

    async def get_idrac_licenses(self) -> List[Dict[str, Any]]:
        try:
            licenses = await self._redfish.get(f"{self._manager_path}/LicenseService/Licenses")
            result = []
            for member in licenses.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        lic_data = await self._redfish.get(url)
                        result.append({
                            "id": lic_data.get("Id", ""),
                            "name": lic_data.get("Name", ""),
                            "license_type": lic_data.get("LicenseType", ""),
                            "status": lic_data.get("Status", {}).get("Health", ""),
                            "raw_data": lic_data,
                        })
                    except Exception:
                        pass
            return result
        except Exception as e:
            logger.debug(f"Failed to get Dell iDRAC licenses: {e}")
            return []

    async def get_bios_attributes(self) -> Dict[str, Any]:
        try:
            bios = await self._redfish.get(f"{self._system_path}/Bios")
            return {
                "current_boot_mode": bios.get("CurrentBootMode", ""),
                "attributes": bios.get("Attributes", {}),
                "raw_data": bios,
            }
        except Exception as e:
            logger.debug(f"Failed to get Dell BIOS attributes: {e}")
            return {}

    async def get_job_queue(self) -> List[Dict[str, Any]]:
        jobs = []
        try:
            job_service = await self._redfish.get(f"{self._manager_path}/Jobs")
            for member in job_service.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        job_data = await self._redfish.get(url)
                        jobs.append({
                            "id": job_data.get("Id", ""), "name": job_data.get("Name", ""),
                            "status": job_data.get("JobStatus", ""), "start_time": job_data.get("StartTime", ""),
                            "percent_complete": job_data.get("PercentComplete", 0), "raw_data": job_data,
                        })
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Failed to get Dell job queue: {e}")
        return jobs

    async def get_raid_controllers(self) -> List[Dict[str, Any]]:
        controllers = []
        try:
            storage = await self._redfish.get(f"{self._system_path}/Storage")
            for member in storage.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        ctrl_data = await self._redfish.get(url)
                        for sc in ctrl_data.get("StorageControllers", []):
                            controllers.append({
                                "id": sc.get("Id", ""), "name": sc.get("Name", ""),
                                "model": sc.get("Model", ""), "firmware": sc.get("FirmwareVersion", ""),
                                "health": sc.get("Status", {}).get("Health", ""),
                                "raid_types_supported": sc.get("SupportedRAIDTypes", []),
                            })
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get Dell RAID controllers: {e}")
        return controllers
