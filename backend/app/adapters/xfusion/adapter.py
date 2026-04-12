from typing import Any, Dict, List

from app.adapters.base.redfish_adapter import RedfishAdapter, _safe_int
from app.adapters.base.registry import register_adapter
from app.adapters.base.types import (
    FirmwareInfo,
    HealthStatus,
    SELEntry,
    StorageController,
    SystemInfo,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


@register_adapter("xfusion")
class XFusionAdapter(RedfishAdapter):
    """xFusion server adapter using iBMC Redfish API.

    References:
    - xFusion Server_Plugin_Ansible (github.com/Open-xFusion/Server_Plugin_Ansible)
    - xFusion iBMC Redfish API docs

    Note: xFusion was spun off from Huawei, and iBMC interfaces are
    highly similar to Huawei's. This adapter reuses the same API patterns.

    xFusion iBMC Redfish extensions:
    - Oem.xFusion namespace for xFusion-specific properties
    - iBMC System Log (same as Huawei)
    - xFusion RAID controllers
    - LCD panel management
    - Out-of-band NIC configuration
    - Virtual media support
    - Boot order configuration
    """

    brand: str = "xfusion"
    supported_models: List[str] = [
        "FusionServer 2288H V6", "FusionServer 2288H V7",
        "FusionServer 2488H V6", "FusionServer 2488H V7",
        "FusionServer 5288H V6", "FusionServer 1288H V7",
    ]

    async def get_system_info(self) -> SystemInfo:
        info = await super().get_system_info()

        try:
            manager = await self._redfish.get(self._manager_path)
            info.bmc_version = manager.get("FirmwareVersion", "")
            info.raw_data["manager"] = manager

            oem = manager.get("Oem", {})
            xfusion_oem = oem.get("xFusion", oem.get("Huawei", {}))
            if xfusion_oem:
                info.raw_data["xfusion_oem"] = xfusion_oem
        except Exception as e:
            logger.debug(f"Failed to get xFusion iBMC manager data: {e}")

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
                logger.debug(f"Failed to get xFusion log from {log_url}: {e}")

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
                        version = fw_data.get("Version", "")

                        oem = fw_data.get("Oem", {})
                        xfusion_oem = oem.get("xFusion", oem.get("Huawei", {}))
                        available_version = xfusion_oem.get("AvailableVersion", "")
                        update_status = "up_to_date"
                        if available_version and available_version != version:
                            update_status = "update_available"

                        firmware_list.append(FirmwareInfo(
                            component=fw_data.get("Name", ""),
                            current_version=version,
                            available_version=available_version,
                            update_status=update_status,
                            component_id=fw_data.get("Id", ""),
                            raw_data=fw_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get xFusion firmware inventory: {e}")

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
                            raw_data=ctrl_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get xFusion storage controllers: {e}")

        return controllers

    async def get_ibmc_info(self) -> Dict[str, Any]:
        try:
            manager = await self._redfish.get(self._manager_path)
            oem = manager.get("Oem", {})
            xfusion_oem = oem.get("xFusion", oem.get("Huawei", {}))
            return {
                "firmware_version": manager.get("FirmwareVersion", ""),
                "model": manager.get("Model", ""),
                "status": manager.get("Status", {}).get("Health", ""),
                "ip_address": self.connection.host,
                "serial_number": xfusion_oem.get("SerialNumber", ""),
                "xfusion_oem": xfusion_oem,
                "raw_data": manager,
            }
        except Exception as e:
            logger.warning(f"Failed to get xFusion iBMC info: {e}")
            return {}

    async def get_lcd_info(self) -> Dict[str, Any]:
        try:
            lcd = await self._redfish.get(f"{self._manager_path}/Oem/xFusion/LCD")
            return {
                "lcd_text": lcd.get("LCDText", ""),
                "lcd_mode": lcd.get("LCDMode", ""),
                "raw_data": lcd,
            }
        except Exception as e:
            logger.debug(f"Failed to get xFusion LCD info: {e}")
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
            logger.debug(f"Failed to get xFusion out-of-band NIC: {e}")
            return {}

    async def get_bios_attributes(self) -> Dict[str, Any]:
        try:
            bios = await self._redfish.get(f"{self._system_path}/Bios")
            oem = bios.get("Oem", {})
            xfusion_oem = oem.get("xFusion", oem.get("Huawei", {}))
            return {
                "current_boot_mode": bios.get("CurrentBootMode", ""),
                "attributes": bios.get("Attributes", {}),
                "xfusion_bios_settings": xfusion_oem.get("Bios", {}),
                "raw_data": bios,
            }
        except Exception as e:
            logger.debug(f"Failed to get xFusion BIOS attributes: {e}")
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
            logger.debug(f"Failed to get xFusion virtual media: {e}")
        return result
