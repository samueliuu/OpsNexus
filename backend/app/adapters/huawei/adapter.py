from typing import Any, Dict, List, Optional

from app.adapters.base.redfish_adapter import RedfishAdapter, _safe_int
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


@register_adapter("huawei")
class HuaweiAdapter(RedfishAdapter):
    """Huawei server adapter using iBMC Redfish API.

    References:
    - Huawei iBMC Redfish API docs
    - python-ibmcclient (github.com/IamFive/python-ibmcclient)
    - xFusion Server_Plugin_Ansible (github.com/Open-xFusion/Server_Plugin_Ansible)

    Note: python-ibmcclient is NOT imported to avoid dependency conflicts.
    We use DMTF python-redfish-library for transport and reference
    Huawei iBMC OEM extensions.

    Huawei iBMC Redfish extensions:
    - Oem.Huawei namespace for Huawei-specific properties
    - iBMC System Log (separate from SEL)
    - Huawei RAID controllers (SR450C, SR130, etc.)
    - Huawei eService integration
    - Huawei FusionServer Pro / TaiShan management
    - LCD panel management
    - Out-of-band NIC configuration
    - Virtual media support
    - Boot order configuration
    """

    brand: str = "huawei"
    supported_models: List[str] = [
        "FusionServer Pro 2288H V5", "FusionServer Pro 2288H V6",
        "FusionServer Pro 2488H V5", "FusionServer Pro 2488H V6",
        "FusionServer Pro 5288H V6",
        "FusionServer Pro 1288H V5", "FusionServer Pro 1288H V7",
        "FusionServer Pro 2288H V7",
        "TaiShan 200 (Model 2280)", "TaiShan 200 (Model 5280)",
        "FusionServer Pro 2298 V5",
    ]

    async def get_system_info(self) -> SystemInfo:
        info = await super().get_system_info()

        try:
            manager = await self._redfish.get(self._manager_path)
            info.bmc_version = manager.get("FirmwareVersion", "")
            info.raw_data["manager"] = manager

            oem = manager.get("Oem", {})
            huawei_oem = oem.get("Huawei", {})
            if huawei_oem:
                info.raw_data["huawei_oem"] = huawei_oem
        except Exception as e:
            logger.debug(f"Failed to get Huawei iBMC manager data: {e}")

        return info

    async def get_sel_logs(self, limit: int = 100) -> List[SELEntry]:
        entries = []
        severity_map = {"OK": "info", "Warning": "warning", "Critical": "critical"}

        log_urls = [
            f"{self._system_path}/LogServices/SEL/Entries",
            f"{self._manager_path}/LogServices/Log/Entries",
        ]

        for log_url in log_urls:
            try:
                log_data = await self._redfish.get(log_url)
                for entry in log_data.get("Members", []):
                    entries.append(SELEntry(
                        record_id=_safe_int(entry.get("Id", "0")),
                        timestamp=entry.get("Created", ""),
                        sensor_type=entry.get("SensorType", ""),
                        sensor_name=str(entry.get("SensorNumber", "")),
                        event_type=entry.get("EventType", ""),
                        severity=severity_map.get(entry.get("Severity", ""), "info"),
                        description=entry.get("Message", ""),
                        raw_data=entry,
                    ))
            except Exception as e:
                logger.debug(f"Failed to get Huawei log from {log_url}: {e}")

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
                        component_name = fw_data.get("Name", "")
                        version = fw_data.get("Version", "")

                        oem = fw_data.get("Oem", {})
                        huawei_oem = oem.get("Huawei", {})
                        available_version = huawei_oem.get("AvailableVersion", "")
                        update_status = "up_to_date"
                        if available_version and available_version != version:
                            update_status = "update_available"

                        firmware_list.append(FirmwareInfo(
                            component=component_name,
                            current_version=version,
                            available_version=available_version,
                            update_status=update_status,
                            component_id=fw_data.get("Id", ""),
                            raw_data=fw_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get Huawei firmware inventory: {e}")

        return firmware_list

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
                                        "id": drive_data.get("Id", ""),
                                        "name": drive_data.get("Name", ""),
                                        "model": drive_data.get("Model", ""),
                                        "capacity_bytes": drive_data.get("CapacityBytes", 0),
                                        "media_type": drive_data.get("MediaType", ""),
                                        "health": drive_data.get("Status", {}).get("Health", ""),
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
                            id=ctrl_data.get("Id", ""),
                            name=ctrl_data.get("Name", ""),
                            model=model,
                            firmware_version=firmware,
                            status=health_map.get(ctrl_data.get("Status", {}).get("Health", ""), HealthStatus.UNKNOWN),
                            drives=drives,
                            raw_data=ctrl_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get Huawei storage controllers: {e}")

        return controllers

    async def get_ibmc_info(self) -> Dict[str, Any]:
        try:
            manager = await self._redfish.get(self._manager_path)
            oem = manager.get("Oem", {}).get("Huawei", {})
            return {
                "firmware_version": manager.get("FirmwareVersion", ""),
                "model": manager.get("Model", ""),
                "status": manager.get("Status", {}).get("Health", ""),
                "ip_address": self.connection.host,
                "serial_number": oem.get("SerialNumber", ""),
                "huawei_oem": oem,
                "raw_data": manager,
            }
        except Exception as e:
            logger.warning(f"Failed to get iBMC info: {e}")
            return {}

    async def get_lcd_info(self) -> Dict[str, Any]:
        try:
            lcd = await self._redfish.get(f"{self._manager_path}/Oem/Huawei/LCD")
            return {
                "lcd_text": lcd.get("LCDText", ""),
                "lcd_mode": lcd.get("LCDMode", ""),
                "raw_data": lcd,
            }
        except Exception as e:
            logger.debug(f"Failed to get Huawei LCD info: {e}")
            return {}

    async def get_outband_nic(self) -> Dict[str, Any]:
        try:
            nics = await self._redfish.get(f"{self._manager_path}/EthernetInterfaces")
            interfaces = []
            for member in nics.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        nic_data = await self._redfish.get(url)
                        interfaces.append({
                            "id": nic_data.get("Id", ""),
                            "ip_addresses": nic_data.get("IPv4Addresses", []),
                            "mac_address": nic_data.get("MACAddress", ""),
                        })
                    except Exception:
                        pass
            return {
                "interfaces": interfaces,
                "raw_data": nics,
            }
        except Exception as e:
            logger.debug(f"Failed to get Huawei out-of-band NIC: {e}")
            return {}

    async def get_boot_options(self) -> Dict[str, Any]:
        try:
            boot = await self._redfish.get(f"{self._system_path}/BootOptions")
            options = []
            for member in boot.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        opt_data = await self._redfish.get(url)
                        options.append({
                            "id": opt_data.get("Id", ""),
                            "name": opt_data.get("Name", ""),
                            "boot_type": opt_data.get("BootType", ""),
                            "enabled": opt_data.get("Enabled", False),
                        })
                    except Exception:
                        pass
            return {
                "boot_source_override_enabled": boot.get("BootSourceOverrideEnabled", ""),
                "boot_source_override_target": boot.get("BootSourceOverrideTarget", ""),
                "options": options,
                "raw_data": boot,
            }
        except Exception as e:
            logger.debug(f"Failed to get Huawei boot options: {e}")
            return {}

    async def get_virtual_media(self) -> List[Dict[str, Any]]:
        result = []
        try:
            vm = await self._redfish.get(f"{self._manager_path}/VirtualMedia")
            for member in vm.get("Members", []):
                url = member.get("@odata.id", "")
                if url:
                    try:
                        vm_data = await self._redfish.get(url)
                        result.append({
                            "id": vm_data.get("Id", ""),
                            "name": vm_data.get("Name", ""),
                            "media_type": vm_data.get("MediaType", ""),
                            "inserted": vm_data.get("Inserted", False),
                            "image_url": vm_data.get("Image", ""),
                            "raw_data": vm_data,
                        })
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Failed to get Huawei virtual media: {e}")
        return result

    async def get_bios_attributes(self) -> Dict[str, Any]:
        try:
            bios = await self._redfish.get(f"{self._system_path}/Bios")
            huawei_oem = bios.get("Oem", {}).get("Huawei", {})
            return {
                "current_boot_mode": bios.get("CurrentBootMode", ""),
                "attributes": bios.get("Attributes", {}),
                "huawei_bios_settings": huawei_oem.get("Bios", {}),
                "raw_data": bios,
            }
        except Exception as e:
            logger.debug(f"Failed to get Huawei BIOS attributes: {e}")
            return {}
