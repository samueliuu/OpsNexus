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


@register_adapter("hpe")
class HPEAdapter(ServerAdapter):
    """HPE server adapter using iLO Redfish API.

    References:
    - HPE iLO 5/6 Redfish API docs (hpe.com/support/ilo5-redfish)
    - HPE python-ilorest-library (github.com/HewlettPackard/python-ilorest-library)
    - HPE iLO Ansible Collection (github.com/HewlettPackard/ilo-ansible-collection)

    Note: python-ilorest-library is NOT imported due to package name conflict
    with DMTF python-redfish-library (both use 'redfish' namespace).
    Instead, we use DMTF library for transport and reference HPE OEM extensions.

    HPE iLO Redfish extensions:
    - Oem.Hpe namespace for HPE-specific properties
    - HpeServerChassis, HpeBios, HpeComputerSystemExt extensions
    - Active Health System (AHS) for diagnostic data
    - Intelligent Provisioning integration
    - iLO License management
    - HPE Smart Storage Administrator (SSA)
    """

    brand: str = "hpe"
    supported_models: List[str] = [
        "ProLiant DL360 Gen10", "ProLiant DL360 Gen10 Plus", "ProLiant DL360 Gen11",
        "ProLiant DL380 Gen10", "ProLiant DL380 Gen10 Plus", "ProLiant DL380 Gen11",
        "ProLiant DL385 Gen10 Plus", "ProLiant DL385 Gen11",
        "ProLiant DL560 Gen10", "ProLiant DL580 Gen10",
        "ProLiant ML350 Gen10", "ProLiant ML350 Gen11",
        "ProLiant XL420 Gen9", "ProLiant XL450 Gen10",
        "Synergy 480 Gen10", "Synergy 660 Gen10",
    ]

    def __init__(self, connection: BMCConnection):
        super().__init__(connection)
        self._redfish = RedfishClient(connection)
        self._system_id: Optional[str] = None
        self._chassis_id: Optional[str] = None
        self._manager_id: Optional[str] = None

    async def connect(self) -> None:
        await self._redfish.connect()
        await self._discover_hpe_ids()

    async def disconnect(self) -> None:
        await self._redfish.disconnect()

    async def _discover_hpe_ids(self) -> None:
        try:
            systems = await self._redfish.get("/redfish/v1/Systems")
            members = systems.get("Members", [])
            if members:
                odata_id = members[0].get("@odata.id", "")
                self._system_id = odata_id.rstrip("/").split("/")[-1]
        except Exception:
            self._system_id = "1"

        try:
            chassis = await self._redfish.get("/redfish/v1/Chassis")
            members = chassis.get("Members", [])
            if members:
                odata_id = members[0].get("@odata.id", "")
                self._chassis_id = odata_id.rstrip("/").split("/")[-1]
        except Exception:
            self._chassis_id = "1"

        try:
            managers = await self._redfish.get("/redfish/v1/Managers")
            for member in managers.get("Members", []):
                url = member.get("@odata.id", "")
                try:
                    mgr_data = await self._redfish.get(url)
                    mgr_type = mgr_data.get("ManagerType", "")
                    if mgr_type == "BMC":
                        self._manager_id = url.rstrip("/").split("/")[-1]
                        break
                except Exception:
                    continue
            if not self._manager_id:
                if managers.get("Members"):
                    odata_id = managers["Members"][0].get("@odata.id", "")
                    self._manager_id = odata_id.rstrip("/").split("/")[-1]
        except Exception:
            self._manager_id = "1"

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
            hpe_oem = oem.get("Hpe", {})
            if hpe_oem:
                info.bmc_version = hpe_oem.get("iLOVersion", "")
                info.raw_data["hpe_oem"] = hpe_oem
        except Exception as e:
            logger.debug(f"Failed to get HPE OEM data from system: {e}")

        try:
            manager = await self._redfish.get(self._manager_path)
            info.bmc_version = manager.get("FirmwareVersion", info.bmc_version)
            info.raw_data["manager"] = manager

            hpe_mgr_oem = manager.get("Oem", {}).get("Hpe", {})
            if hpe_mgr_oem:
                info.raw_data["hpe_manager_oem"] = hpe_mgr_oem
                if not info.bmc_version:
                    info.bmc_version = hpe_mgr_oem.get("ManagerFirmwareVersion", "")
        except Exception as e:
            logger.debug(f"Failed to get HPE iLO manager data: {e}")

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
            logger.warning(f"Failed to get HPE thermal data: {e}")

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
            logger.warning(f"Failed to get HPE power data: {e}")

        return sensors

    async def get_sel_logs(self, limit: int = 100) -> List[SELEntry]:
        entries = []
        severity_map = {"OK": "info", "Warning": "warning", "Critical": "critical"}

        log_urls = [
            f"{self._manager_path}/LogServices/IEL/Entries",
            f"{self._system_path}/LogServices/IML/Entries",
        ]

        for log_url in log_urls:
            try:
                log_data = await self._redfish.get(log_url)
                for entry in log_data.get("Members", []):
                    entries.append(SELEntry(
                        record_id=int(entry.get("Id", "0")),
                        timestamp=entry.get("Created", ""),
                        sensor_type=entry.get("SensorType", ""),
                        sensor_name=str(entry.get("SensorNumber", "")),
                        event_type=entry.get("EventType", ""),
                        severity=severity_map.get(entry.get("Severity", ""), "info"),
                        description=entry.get("Message", ""),
                        raw_data=entry,
                    ))
            except Exception as e:
                logger.debug(f"Failed to get HPE log from {log_url}: {e}")

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
                        hpe_oem = fw_data.get("Oem", {}).get("Hpe", {})
                        if hpe_oem.get("UpdateStatus") == "Available":
                            update_status = "update_available"

                        firmware_list.append(FirmwareInfo(
                            component=fw_data.get("Name", ""),
                            current_version=fw_data.get("Version", ""),
                            available_version=hpe_oem.get("AvailableVersion", ""),
                            update_status=update_status,
                            component_id=fw_data.get("Id", ""),
                            raw_data=fw_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get HPE firmware inventory: {e}")

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
            logger.warning(f"Failed to get HPE network adapters: {e}")
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
                            raw_data=ctrl_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get HPE storage controllers: {e}")
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
            logger.warning(f"Failed to get HPE power supplies: {e}")
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
            logger.warning(f"Failed to get HPE fans: {e}")
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
            logger.warning(f"Failed to get HPE memory: {e}")
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
            logger.warning(f"Failed to get HPE processors: {e}")
        return processors

    async def get_ilo_info(self) -> Dict[str, Any]:
        try:
            manager = await self._redfish.get(self._manager_path)
            hpe_oem = manager.get("Oem", {}).get("Hpe", {})
            return {
                "firmware_version": manager.get("FirmwareVersion", ""),
                "model": manager.get("Model", ""),
                "status": manager.get("Status", {}).get("Health", ""),
                "ip_address": self.connection.host,
                "ilo_type": hpe_oem.get("ManagerType", "iLO 5"),
                "license_type": hpe_oem.get("License", {}).get("LicenseType", ""),
                "hpe_oem": hpe_oem,
                "raw_data": manager,
            }
        except Exception as e:
            logger.warning(f"Failed to get HPE iLO info: {e}")
            return {}

    async def get_ilo_licenses(self) -> List[Dict[str, Any]]:
        try:
            license_service = await self._redfish.get(f"{self._manager_path}/LicenseService")
            result = []
            for lic_member in license_service.get("Licenses", []):
                url = lic_member.get("@odata.id", "")
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
            logger.debug(f"Failed to get HPE iLO licenses (may not exist on this iLO version): {e}")
            return []

    async def get_bios_attributes(self) -> Dict[str, Any]:
        try:
            bios = await self._redfish.get(f"{self._system_path}/Bios")
            hpe_oem = bios.get("Oem", {}).get("Hpe", {})
            return {
                "current_boot_mode": bios.get("CurrentBootMode", ""),
                "attributes": bios.get("Attributes", {}),
                "hpe_bios_settings": hpe_oem.get("Bios", {}),
                "raw_data": bios,
            }
        except Exception as e:
            logger.debug(f"Failed to get HPE BIOS attributes: {e}")
            return {}

    async def get_active_health_system_status(self) -> Dict[str, Any]:
        try:
            ahs = await self._redfish.get(f"{self._system_path}/ActiveHealthSystem")
            return {
                "enabled": ahs.get("AHSStatus", "") == "Enabled",
                "location": ahs.get("Location", ""),
                "start_time": ahs.get("StartTime", ""),
                "end_time": ahs.get("EndTime", ""),
                "raw_data": ahs,
            }
        except Exception as e:
            logger.debug(f"Failed to get HPE AHS status: {e}")
            return {}

    async def get_smart_storage(self) -> Dict[str, Any]:
        try:
            storage = await self._redfish.get(f"{self._system_path}/SmartStorage")
            return {
                "status": storage.get("Status", {}).get("Health", ""),
                "array_controllers_url": storage.get("ArrayControllers", {}).get("@odata.id", ""),
                "raw_data": storage,
            }
        except Exception as e:
            logger.debug(f"Failed to get HPE Smart Storage info: {e}")
            return {}
