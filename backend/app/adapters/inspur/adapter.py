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


@register_adapter("inspur")
class InspurAdapter(RedfishAdapter):
    """Inspur server adapter using OpenRMC/ISBMC Redfish API.

    References:
    - Inspur OpenRMC Redfish API docs
    - Inspur ISBMC management interface
    - OpenBMC standard (Inspur OpenRMC is based on OpenBMC)

    Inspur BMC Redfish extensions:
    - OpenRMC based on OpenBMC (Redfish v1.6+)
    - Oem.Inspur namespace for Inspur-specific properties
    - Inspur-specific storage management
    - Inspur BIOS configuration
    - Virtual media support
    """

    brand: str = "inspur"
    supported_models: List[str] = [
        "NF5280M6", "NF5280M7", "NF5270M6", "NF5270M7",
        "NF5180M6", "NF5180M7", "NF8480M6", "NF8480M7",
        "NF5468M6", "NF5468A7", "NF8260M6",
    ]

    async def get_system_info(self) -> SystemInfo:
        info = await super().get_system_info()

        try:
            manager = await self._redfish.get(self._manager_path)
            info.bmc_version = manager.get("FirmwareVersion", "")
            info.raw_data["manager"] = manager

            oem = manager.get("Oem", {})
            inspur_oem = oem.get("Inspur", {})
            if inspur_oem:
                info.raw_data["inspur_oem"] = inspur_oem
        except Exception as e:
            logger.debug(f"Failed to get Inspur BMC manager data: {e}")

        return info

    async def get_sel_logs(self, limit: int = 100) -> List[SELEntry]:
        entries = []
        severity_map = {"OK": "info", "Warning": "warning", "Critical": "critical"}

        log_urls = [
            f"{self._system_path}/LogServices/SEL/Entries",
            f"{self._manager_path}/LogServices/EventLog/Entries",
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
                logger.debug(f"Failed to get Inspur log from {log_url}: {e}")

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
                        inspur_oem = fw_data.get("Oem", {}).get("Inspur", {})
                        if inspur_oem.get("UpdateStatus") == "Available":
                            update_status = "update_available"

                        firmware_list.append(FirmwareInfo(
                            component=fw_data.get("Name", ""),
                            current_version=fw_data.get("Version", ""),
                            available_version=inspur_oem.get("AvailableVersion", ""),
                            update_status=update_status,
                            component_id=fw_data.get("Id", ""),
                            raw_data=fw_data,
                        ))
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to get Inspur firmware inventory: {e}")

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
            logger.warning(f"Failed to get Inspur storage controllers: {e}")

        return controllers

    async def get_bmc_info(self) -> Dict[str, Any]:
        try:
            manager = await self._redfish.get(self._manager_path)
            inspur_oem = manager.get("Oem", {}).get("Inspur", {})
            return {
                "firmware_version": manager.get("FirmwareVersion", ""),
                "model": manager.get("Model", ""),
                "status": manager.get("Status", {}).get("Health", ""),
                "ip_address": self.connection.host,
                "inspur_oem": inspur_oem,
                "raw_data": manager,
            }
        except Exception as e:
            logger.warning(f"Failed to get Inspur BMC info: {e}")
            return {}

    async def get_bios_attributes(self) -> Dict[str, Any]:
        try:
            bios = await self._redfish.get(f"{self._system_path}/Bios")
            inspur_oem = bios.get("Oem", {}).get("Inspur", {})
            return {
                "current_boot_mode": bios.get("CurrentBootMode", ""),
                "attributes": bios.get("Attributes", {}),
                "inspur_bios_settings": inspur_oem.get("Bios", {}),
                "raw_data": bios,
            }
        except Exception as e:
            logger.debug(f"Failed to get Inspur BIOS attributes: {e}")
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
            logger.debug(f"Failed to get Inspur virtual media: {e}")
        return result
