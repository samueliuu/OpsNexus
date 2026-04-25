# 适配器架构

## 设计理念

OpsNexus 需要统一管理 8 大品牌的服务器，各品牌 BMC 管理接口存在差异。适配器架构通过 **适配器模式 + 注册表模式** 实现品牌差异的透明化，上层业务代码无需关心底层通信细节。

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     业务层 (Service)                         │
│              BMCService / MetricCollectionService            │
└──────────────────────────┬──────────────────────────────────┘
                           │ AdapterRegistry.create(brand, conn)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    适配器注册表 (Registry)                    │
│                                                             │
│  @register_adapter("dell")     → DellAdapter               │
│  @register_adapter("hpe")      → HPEAdapter                │
│  @register_adapter("lenovo")   → LenovoAdapter             │
│  @register_adapter("huawei")   → HuaweiAdapter             │
│  @register_adapter("inspur")   → InspurAdapter             │
│  @register_adapter("h3c")      → H3CAdapter                │
│  @register_adapter("sugon")    → SugonAdapter              │
│  @register_adapter("xfusion")  → XFusionAdapter            │
└──────────────────────────┬──────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
┌─────────────────────┐       ┌─────────────────────┐
│   ServerAdapter     │       │   ServerAdapter     │
│   (ABC, 14 方法)    │       │   (ABC, 14 方法)    │
│         ▲           │       │         ▲           │
│         │           │       │         │           │
│  RedfishAdapter     │       │  DellAdapter        │
│  (通用 Redfish)     │       │  (iDRAC 独立实现)   │
│    ▲  ▲  ▲  ▲  ▲   │       │                     │
│    │  │  │  │  │    │       └─────────────────────┘
│    │  │  │  │  │    │
│  Huawei Inspur H3C  │       ┌─────────────────────┐
│  Sugon  xFusion     │       │   ServerAdapter     │
│                     │       │         ▲           │
└─────────────────────┘       │  HPEAdapter         │
                              │  (iLO 独立实现)     │
                              └─────────────────────┘
                              ┌─────────────────────┐
                              │   ServerAdapter     │
                              │         ▲           │
                              │  LenovoAdapter      │
                              │  (XCC 独立实现)     │
                              └─────────────────────┘
```

## 核心组件

### ServerAdapter 抽象基类

定义 14 个抽象方法，所有品牌适配器必须实现：

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `connect()` | None | 建立 BMC 连接 |
| `disconnect()` | None | 断开 BMC 连接 |
| `get_system_info()` | SystemInfo | 获取系统信息 |
| `get_power_state()` | PowerState | 获取电源状态 |
| `set_power_action(action)` | PowerState | 执行电源操作 |
| `get_sensor_data()` | List[SensorData] | 获取传感器数据 |
| `get_sel_logs()` | List[SELEntry] | 获取 SEL 日志 |
| `get_firmware_inventory()` | List[FirmwareInfo] | 获取固件清单 |
| `get_network_adapters()` | List[NetworkAdapter] | 获取网络适配器 |
| `get_storage_controllers()` | List[StorageController] | 获取存储控制器 |
| `get_power_supplies()` | List[PowerSupply] | 获取电源模块 |
| `get_fans()` | List[Fan] | 获取风扇信息 |
| `get_memory()` | List[MemoryModule] | 获取内存信息 |
| `get_processors()` | List[Processor] | 获取处理器信息 |

支持 `async with` 上下文管理器，自动调用 `connect()` / `disconnect()`。

### AdapterRegistry 注册表

```python
class AdapterRegistry:
    _adapters: Dict[str, Type[ServerAdapter]] = {}

    @classmethod
    def register_adapter(cls, brand: str):
        """装饰器，注册品牌适配器"""
        def decorator(adapter_cls):
            cls._adapters[brand] = adapter_cls
            return adapter_cls
        return decorator

    @classmethod
    def create(cls, brand: str, connection: BMCConnection) -> ServerAdapter:
        """工厂方法，根据品牌创建适配器实例"""
        adapter_cls = cls._adapters.get(brand)
        if not adapter_cls:
            raise ValueError(f"Unsupported brand: {brand}")
        return adapter_cls(connection)

    @classmethod
    def detect_brand(cls, manufacturer: str) -> str:
        """通过制造商字符串自动检测品牌"""

    @classmethod
    def auto_create(cls, connection: BMCConnection) -> ServerAdapter:
        """自动检测品牌并创建适配器"""
```

### RedfishClient 通信客户端

```python
class RedfishClient:
    """Redfish API 通信客户端"""

    def __init__(self, connection: BMCConnection):
        # DMTF python-redfish-library 会话管理
        # httpx.AsyncClient 异步并发操作

    async def get(self, path: str) -> dict:
        """GET 请求（优先 httpx 异步，降级 DMTF 同步）"""

    async def post(self, path: str, data: dict) -> dict:
        """POST 请求"""
```

特性：
- **双模式通信**：优先 httpx 异步通道，DMTQ 同步操作通过 `asyncio.to_thread()` 降级
- **自签名证书**：`verify_ssl=False` 支持 BMC 常见的自签名证书
- **会话管理**：DMTQ Redfish 库维护会话

## 数据类型定义

### 枚举类型

```python
class PowerState(str, Enum):
    ON = "on"
    OFF = "off"
    POWERING_ON = "powering_on"
    POWERING_OFF = "powering_off"
    REBOOT = "reboot"
    UNKNOWN = "unknown"

class PowerAction(str, Enum):
    ON = "on"
    OFF = "off"
    GRACEFUL_OFF = "graceful_off"
    FORCE_OFF = "force_off"
    RESTART = "restart"
    GRACEFUL_RESTART = "graceful_restart"
    FORCE_RESTART = "force_restart"
    NMI = "nmi"
```

### 数据类

```python
@dataclass
class BMCConnection:
    host: str
    username: str
    password: str
    protocol: str = "redfish"
    port: int = 443
    verify_ssl: bool = False
    timeout: int = 30

@dataclass
class SystemInfo:
    manufacturer: str
    model: str
    serial_number: str
    bios_version: str
    bmc_version: str
    power_state: PowerState
    health_status: str
    cpu_info: Optional[str] = None
    memory_gb: Optional[int] = None

@dataclass
class SensorData:
    name: str
    reading: Optional[float]
    unit: str
    status: str
    sensor_type: str
    thresholds: Optional[dict] = None

@dataclass
class SELEntry:
    record_id: int
    timestamp: str
    sensor_type: str
    sensor_name: str
    event_type: str
    severity: str
    description: str

@dataclass
class FirmwareInfo:
    component: str
    current_version: str
    available_version: Optional[str] = None
    update_status: Optional[str] = None
```

## 品牌适配器详解

### DellAdapter（iDRAC）

| 特性 | 说明 |
|------|------|
| 继承 | ServerAdapter（独立实现） |
| 管理接口 | iDRAC |
| 支持型号 | PowerEdge R650/R750/R740/R640/R940 等 14+ |
| 特有功能 | iDRAC 固定 ID（System.Embedded.1）、OEM 数据提取、iDRAC 许可证查询、BIOS 属性、Job 队列管理、RAID 控制器信息 |

关键实现：
- 使用 iDRAC 固定 URI 模式（`/redfish/v1/Systems/System.Embedded.1`）
- 提取 `Oem.Dell` 扩展数据
- 支持 iDRAC Job 队列操作

### HPEAdapter（iLO）

| 特性 | 说明 |
|------|------|
| 继承 | ServerAdapter（独立实现） |
| 管理接口 | iLO |
| 支持型号 | ProLiant DL380/DL360/ML350 等 16+ |
| 特有功能 | iLO ManagerType=BMC 发现、HPE OEM 数据、iLO 许可证、Active Health System、Smart Storage |

关键实现：
- 通过 `ManagerType=BMC` 发现 iLO 管理控制器
- 提取 `Oem.Hpe` 扩展数据
- Smart Storage 逻辑驱动器信息

### LenovoAdapter（XCC）

| 特性 | 说明 |
|------|------|
| 继承 | ServerAdapter（独立实现） |
| 管理接口 | XCC |
| 支持型号 | ThinkSystem SR650/SR630/ST650 等 16+ |
| 特有功能 | XCC 信息、FFDC（首次故障数据捕获）、VPD（产品数据）、BIOS 属性 |

关键实现：
- 提取 `Oem.Lenovo` 扩展数据
- FFDC 日志收集
- VPD 产品信息

### HuaweiAdapter（iBMC）

| 特性 | 说明 |
|------|------|
| 继承 | RedfishAdapter |
| 管理接口 | iBMC |
| 支持型号 | FusionServer Pro 2288H/2488H、TaiShan 200 等 11+ |
| 特有功能 | iBMC OEM 扩展、LCD 面板、带外 NIC、启动选项、虚拟媒体、BIOS 属性 |

关键实现：
- 继承 RedfishAdapter 通用实现
- 扩展 `Oem.Huawei` 特有数据
- iBMC 虚拟媒体和启动选项

### InspurAdapter（OpenRMC）

| 特性 | 说明 |
|------|------|
| 继承 | RedfishAdapter |
| 管理接口 | OpenRMC |
| 支持型号 | NF5280M6/NF5270M6 等 11+ |
| 特有功能 | OpenRMC OEM 数据、BIOS 属性、虚拟媒体 |

### H3CAdapter（HDM）

| 特性 | 说明 |
|------|------|
| 继承 | RedfishAdapter |
| 管理接口 | HDM |
| 支持型号 | R4900/R4700 等 9+ |
| 特有功能 | HDM 信息、HDM 版本、BIOS 属性、虚拟媒体 |

### SugonAdapter

| 特性 | 说明 |
|------|------|
| 继承 | RedfishAdapter |
| 管理接口 | BMC |
| 支持型号 | I620-G30/A620-G30 等 9+ |
| 特有功能 | IPMI 降级提示、BIOS 属性 |

### XFusionAdapter（iBMC 兼容）

| 特性 | 说明 |
|------|------|
| 继承 | RedfishAdapter |
| 管理接口 | iBMC |
| 支持型号 | FusionServer 2288H/2488H 等 6+ |
| 特有功能 | 兼容华为 iBMC 接口（Oem.xFusion / Oem.Huawei 双兼容）、LCD 面板、带外 NIC、虚拟媒体、BIOS 属性 |

关键实现：
- 同时支持 `Oem.xFusion` 和 `Oem.Huawei` 扩展数据
- 与华为 iBMC 接口高度兼容

## 品牌自动检测

`AdapterRegistry.auto_create()` 实现品牌自动检测：

```python
MANUFACTURER_BRAND_MAP = {
    "Dell Inc.": "dell",
    "Dell EMC": "dell",
    "HPE": "hpe",
    "Hewlett Packard Enterprise": "hpe",
    "HP": "hpe",
    "Lenovo": "lenovo",
    "Huawei": "huawei",
    "Inspur": "inspur",
    "H3C": "h3c",
    "Sugon": "sugon",
    "x Fusion": "xfusion",
    "xFusion": "xfusion",
    "Supermicro": "supermicro",
}
```

流程：
1. 使用通用 Redfish 连接 BMC
2. 读取 `/redfish/v1/Systems` 获取 `Manufacturer` 字段
3. 通过 `MANUFACTURER_BRAND_MAP` 映射到品牌键
4. 创建对应品牌适配器实例

## 扩展新品牌

添加新品牌适配器只需 3 步：

1. **创建适配器类**：

```python
# backend/app/adapters/newbrand/adapter.py
from app.adapters.base.adapter import ServerAdapter
from app.adapters.base.registry import AdapterRegistry, register_adapter

@register_adapter("newbrand")
class NewBrandAdapter(ServerAdapter):
    def __init__(self, connection: BMCConnection):
        super().__init__(connection)
        # 初始化

    async def connect(self):
        # 实现连接逻辑

    async def get_system_info(self) -> SystemInfo:
        # 实现系统信息获取
        ...
```

2. **创建 `__init__.py`**：

```python
from app.adapters.newbrand.adapter import NewBrandAdapter
```

3. **在适配器包中导入**（确保注册）：

```python
# backend/app/adapters/__init__.py
import app.adapters.newbrand  # 触发 @register_adapter 装饰器
```
