from typing import Dict, List, Optional, Type

from app.adapters.base.adapter import ServerAdapter
from app.adapters.base.types import BMCConnection
from app.core.exceptions import ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)

MANUFACTURER_BRAND_MAP = {
    "dell": "dell",
    "dell inc.": "dell",
    "hpe": "hpe",
    "hewlett packard enterprise": "hpe",
    "hp": "hpe",
    "huawei": "huawei",
    "lenovo": "lenovo",
    "h3c": "h3c",
    "new h3c": "h3c",
    "inspur": "inspur",
    "sugon": "sugon",
    "xfusion": "xfusion",
    "supermicro": "generic",
    "fujitsu": "generic",
    "cisco": "generic",
}


class AdapterRegistry:
    _adapters: Dict[str, Type[ServerAdapter]] = {}

    @classmethod
    def register(cls, brand: str, adapter_class: Type[ServerAdapter]) -> None:
        cls._adapters[brand.lower()] = adapter_class

    @classmethod
    def get(cls, brand: str) -> Optional[Type[ServerAdapter]]:
        return cls._adapters.get(brand.lower())

    @classmethod
    def create(cls, brand: str, connection: BMCConnection) -> ServerAdapter:
        adapter_class = cls.get(brand)
        if not adapter_class:
            supported = ", ".join(sorted(cls._adapters.keys()))
            raise ValidationException(
                f"Unsupported brand: '{brand}'. Supported brands: {supported}"
            )
        return adapter_class(connection)

    @classmethod
    def list_brands(cls) -> List[str]:
        return sorted(cls._adapters.keys())

    @classmethod
    def is_supported(cls, brand: str) -> bool:
        return brand.lower() in cls._adapters

    @classmethod
    async def detect_brand(cls, connection: BMCConnection) -> str:
        """Auto-detect server brand by connecting to BMC and reading manufacturer.

        Connects to BMC via Redfish, reads the Manufacturer field from
        /redfish/v1/Systems, and maps it to a registered brand adapter.
        Falls back to 'generic' if the manufacturer is not recognized.
        """
        from app.adapters.base.redfish import RedfishClient

        client = RedfishClient(connection)
        try:
            await client.connect()

            systems = await client.get("/redfish/v1/Systems")
            members = systems.get("Members", [])
            if not members:
                return "generic"

            system_url = members[0].get("@odata.id", "")
            if not system_url:
                return "generic"

            system_data = await client.get(system_url)
            manufacturer = system_data.get("Manufacturer", "").strip().lower()

            brand = MANUFACTURER_BRAND_MAP.get(manufacturer)
            if brand and cls.is_supported(brand):
                logger.info(f"Auto-detected brand '{brand}' from manufacturer '{manufacturer}'")
                return brand

            for key, mapped_brand in MANUFACTURER_BRAND_MAP.items():
                if key in manufacturer:
                    if cls.is_supported(mapped_brand):
                        logger.info(f"Auto-detected brand '{mapped_brand}' from manufacturer '{manufacturer}'")
                        return mapped_brand

            logger.info(f"Unknown manufacturer '{manufacturer}', falling back to 'generic'")
            return "generic"

        except Exception as e:
            logger.warning(f"Failed to auto-detect brand: {e}, falling back to 'generic'")
            return "generic"
        finally:
            await client.disconnect()

    @classmethod
    async def auto_create(cls, connection: BMCConnection) -> ServerAdapter:
        """Auto-detect brand and create the appropriate adapter instance."""
        brand = await cls.detect_brand(connection)
        return cls.create(brand, connection)


def register_adapter(brand: str):
    def decorator(cls: Type[ServerAdapter]) -> Type[ServerAdapter]:
        AdapterRegistry.register(brand, cls)
        cls.brand = brand
        return cls
    return decorator
