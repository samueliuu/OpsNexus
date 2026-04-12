from typing import Any, Dict, List

from app.adapters.base.redfish_adapter import RedfishAdapter, _safe_int
from app.adapters.base.registry import register_adapter
from app.adapters.base.types import (
    SELEntry,
    SystemInfo,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


@register_adapter("sugon")
class SugonAdapter(RedfishAdapter):
    """Sugon server adapter using BMC Redfish API with IPMI fallback.

    References:
    - Sugon BMC management interface docs
    - Sugon I620/I840/A620/A840 series management

    Sugon BMC characteristics:
    - Limited Redfish support (varies by model)
    - Primary management via IPMI protocol
    - Oem.Sugon namespace for Sugon-specific properties
    - Sugon Advanced Management Module (AMM)

    This adapter extends RedfishAdapter with:
    - IPMI fallback when Redfish endpoints are unavailable
    - Sugon-specific OEM data extraction
    """

    brand: str = "sugon"
    supported_models: List[str] = [
        "I620-G30", "I620-G35", "I840-G30", "I840-G35",
        "I620-G25", "A620-G30", "A840-G30",
        "I450-G20", "I640-G30",
    ]

    async def get_system_info(self) -> SystemInfo:
        info = await super().get_system_info()

        try:
            manager = await self._redfish.get(self._manager_path)
            info.bmc_version = manager.get("FirmwareVersion", "")
            info.raw_data["manager"] = manager

            oem = manager.get("Oem", {})
            sugon_oem = oem.get("Sugon", {})
            if sugon_oem:
                info.raw_data["sugon_oem"] = sugon_oem
        except Exception as e:
            logger.debug(f"Failed to get Sugon BMC manager data: {e}")

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
                logger.debug(f"Failed to get Sugon log from {log_url}: {e}")

        if not entries:
            logger.info("No SEL logs via Redfish, IPMI fallback may be needed for Sugon BMC")

        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:limit]

    async def get_bmc_info(self) -> Dict[str, Any]:
        try:
            manager = await self._redfish.get(self._manager_path)
            sugon_oem = manager.get("Oem", {}).get("Sugon", {})
            return {
                "firmware_version": manager.get("FirmwareVersion", ""),
                "model": manager.get("Model", ""),
                "status": manager.get("Status", {}).get("Health", ""),
                "ip_address": self.connection.host,
                "sugon_oem": sugon_oem,
                "raw_data": manager,
            }
        except Exception as e:
            logger.warning(f"Failed to get Sugon BMC info: {e}")
            return {}

    async def get_bios_attributes(self) -> Dict[str, Any]:
        try:
            bios = await self._redfish.get(f"{self._system_path}/Bios")
            sugon_oem = bios.get("Oem", {}).get("Sugon", {})
            return {
                "current_boot_mode": bios.get("CurrentBootMode", ""),
                "attributes": bios.get("Attributes", {}),
                "sugon_bios_settings": sugon_oem.get("Bios", {}),
                "raw_data": bios,
            }
        except Exception as e:
            logger.debug(f"Failed to get Sugon BIOS attributes: {e}")
            return {}
