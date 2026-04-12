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


@register_adapter("h3c")
class H3CAdapter(RedfishAdapter):
    """H3C server adapter using HDM (Hardware Device Manager) Redfish API.

    References:
    - H3C HDM Ansible Collection (github.com/H3C-BMC/HDM-ansible-collection)
    - H3C HDM/HDM2/HDM3 Redfish API docs

    H3C HDM Redfish extensions:
    - Oem.H3C namespace for H3C-specific properties
    - HDM/HDM2/HDM3 version differences
    - H3C RAID controller management
    - H3C power capping
    - H3C BIOS configuration
    - H3C virtual media
    """

    brand: str = "h3c"
    supported_models: List[str] = [
        "R4900 G3", "R4900 G5", "R4700 G3", "R4700 G5",
        "R4300 G3", "R5300 G4", "R5300 G5", "R5500 G5",
        "R5500 G6", "H3C UniServer R4900 G5",
    ]

    async def get_system_info(self) -> SystemInfo:
        info = await super().get_system_info()

        try:
            manager = await self._redfish.get(self._manager_path)
            info.bmc_version = manager.get("FirmwareVersion", "")
            info.raw_data["manager"] = manager

            oem = manager.get("Oem", {})
            h3c_oem = oem.get("H3C", {})
            if h3c_oem:
                info.raw_data["h3c_oem"] = h3c_oem
        except Exception as e:
            logger.debug(f"Failed to get H3C HDM manager data: {e}")

        return info

    async def get_sel_logs(self, limit: int = 100) -> List[SELEntry]:
        entries = []
        severity_map = {"OK": "info", "Warning": "warning", "Critical": "critical"}

        log_urls = [
            f"{self._system_path}/LogServices/SEL/Entries",
            f"{self._manager_path}/LogServices/Log1/Entries",
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
                logger.debug(f"Failed to get H3C log from {log_url}: {e}")

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
                        h3c_oem = fw_data.get("Oem", {}).get("H3C", {})
                        if h3c_oem.get("UpdateStatus") == "Available":
                            update_status = "update_available"

                        firmware_list.append(FirmwareInfo(
                            component=fw_data.get("Name", ""),
                            current_version=fw_data.get("Version", ""),
                            available_version=h3c_oem.get("AvailableVersion", ""),
                            update_status=update_status,
                            component_id=fw_data.get("Id", ""),
                            raw_data=fw_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get H3C firmware inventory: {e}")

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
            logger.warning(f"Failed to get H3C storage controllers: {e}")

        return controllers

    async def get_hdm_info(self) -> Dict[str, Any]:
        try:
            manager = await self._redfish.get(self._manager_path)
            h3c_oem = manager.get("Oem", {}).get("H3C", {})
            return {
                "firmware_version": manager.get("FirmwareVersion", ""),
                "model": manager.get("Model", ""),
                "status": manager.get("Status", {}).get("Health", ""),
                "ip_address": self.connection.host,
                "hdm_version": h3c_oem.get("HDMVersion", ""),
                "h3c_oem": h3c_oem,
                "raw_data": manager,
            }
        except Exception as e:
            logger.warning(f"Failed to get H3C HDM info: {e}")
            return {}

    async def get_bios_attributes(self) -> Dict[str, Any]:
        try:
            bios = await self._redfish.get(f"{self._system_path}/Bios")
            h3c_oem = bios.get("Oem", {}).get("H3C", {})
            return {
                "current_boot_mode": bios.get("CurrentBootMode", ""),
                "attributes": bios.get("Attributes", {}),
                "h3c_bios_settings": h3c_oem.get("Bios", {}),
                "raw_data": bios,
            }
        except Exception as e:
            logger.debug(f"Failed to get H3C BIOS attributes: {e}")
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
            logger.debug(f"Failed to get H3C virtual media: {e}")
        return result
