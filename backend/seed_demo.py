"""
OpsNexus 全量种子数据脚本 - 用于软著申请演示
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import func, insert, select

from app.core.database import AsyncSessionLocal, init_db
from app.modules.system.models import User, Role, Permission, user_roles, role_permissions, SystemConfig, NotificationChannel
from app.modules.asset.models import DataCenter, Rack, Server
from app.modules.monitor.models import MetricDefinition, AlertRule, AlertEvent
from app.modules.outband.models import SELLog, FirmwareInventory, KVMSession
from app.modules.audit.models import AuditLog, NotificationLog
from app.modules.knowledge.models import Conversation, ConversationMessage, KnowledgeFavorite
from app.modules.autoops.models import TaskDefinition, TaskInstance, TaskStepLog, FirmwarePackage, InspectionPolicy
from app.modules.knowledge.seed import seed_knowledge_data

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
now = datetime.now(timezone.utc)

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OPERATOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
VIEWER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
SUPERADMIN_ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
OPERATOR_ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")
VIEWER_ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000012")
DC_BJ = uuid.UUID("10000000-0000-0000-0000-000000000001")
DC_SH = uuid.UUID("10000000-0000-0000-0000-000000000002")
DC_GZ = uuid.UUID("10000000-0000-0000-0000-000000000003")
R_BJ_A01 = uuid.UUID("11000000-0000-0000-0000-000000000001")
R_BJ_A02 = uuid.UUID("11000000-0000-0000-0000-000000000002")
R_BJ_B01 = uuid.UUID("11000000-0000-0000-0000-000000000003")
R_SH_A01 = uuid.UUID("11000000-0000-0000-0000-000000000004")
R_SH_A02 = uuid.UUID("11000000-0000-0000-0000-000000000005")
R_GZ_A01 = uuid.UUID("11000000-0000-0000-0000-000000000006")


def _sid(i):
    return uuid.UUID(f"30000000-0000-0000-0000-{i:012d}")


async def seed_all():
    await init_db()
    async with AsyncSessionLocal() as session:
        cnt = (await session.execute(select(func.count(User.id)))).scalar_one()
        if cnt > 0:
            print("数据库已有数据，跳过")
            return

        print("插入种子数据...")

        # --- 权限 ---
        perm_defs = [
            ("system:user:read", "查看用户", "system", "read"),
            ("system:user:write", "管理用户", "system", "write"),
            ("system:role:read", "查看角色", "system", "read"),
            ("system:role:write", "管理角色", "system", "write"),
            ("system:config:read", "查看配置", "system", "read"),
            ("system:config:write", "修改配置", "system", "write"),
            ("system:channel:read", "查看通知渠道", "system", "read"),
            ("system:channel:write", "管理通知渠道", "system", "write"),
            ("asset:datacenter:read", "查看数据中心", "asset", "read"),
            ("asset:datacenter:write", "管理数据中心", "asset", "write"),
            ("asset:server:read", "查看服务器", "asset", "read"),
            ("asset:server:write", "管理服务器", "asset", "write"),
            ("monitor:metric:read", "查看监控指标", "monitor", "read"),
            ("monitor:metric:write", "管理监控指标", "monitor", "write"),
            ("monitor:alert:read", "查看告警规则", "monitor", "read"),
            ("monitor:alert:write", "管理告警规则", "monitor", "write"),
            ("monitor:alert:execute", "执行告警操作", "monitor", "execute"),
            ("monitor:collect:execute", "执行监控采集", "monitor", "execute"),
            ("outband:info:read", "查看带外信息", "outband", "read"),
            ("outband:power:execute", "执行电源操作", "outband", "execute"),
            ("outband:kvm:execute", "执行KVM操作", "outband", "execute"),
            ("outband:sel:read", "查看SEL日志", "outband", "read"),
            ("outband:sel:write", "管理SEL日志", "outband", "write"),
            ("audit:log:read", "查看审计日志", "audit", "read"),
            ("audit:log:write", "管理审计日志", "audit", "write"),
            ("audit:notification:execute", "执行通知操作", "audit", "execute"),
            ("autoops:task:read", "查看自动化任务", "autoops", "read"),
            ("autoops:task:write", "管理自动化任务", "autoops", "write"),
            ("autoops:task:execute", "执行自动化任务", "autoops", "execute"),
            ("autoops:task:approve", "审批自动化任务", "autoops", "approve"),
            ("knowledge:read", "查看知识库", "knowledge", "read"),
            ("knowledge:write", "管理知识库", "knowledge", "write"),
        ]
        pm = {}
        for i, (c, n, r, a) in enumerate(perm_defs):
            pid = uuid.UUID(f"20000000-0000-0000-0000-{i+1:012d}")
            pm[c] = pid
            session.add(Permission(id=pid, code=c, name=n, resource=r, action=a, is_builtin=True))
        await session.flush()

        # --- 角色 ---
        session.add(Role(id=SUPERADMIN_ROLE_ID, name="超级管理员", code="superadmin", description="拥有系统全部权限", is_builtin=True, data_scope="all"))
        session.add(Role(id=OPERATOR_ROLE_ID, name="运维工程师", code="operator", description="负责日常运维操作", is_builtin=True, data_scope="all"))
        session.add(Role(id=VIEWER_ROLE_ID, name="只读用户", code="viewer", description="仅查看数据", is_builtin=True, data_scope="all"))
        await session.flush()

        for c in pm:
            await session.execute(insert(role_permissions).values(role_id=SUPERADMIN_ROLE_ID, permission_id=pm[c]))
        operator_perms = [
            "system:user:read", "system:role:read", "system:config:read", "system:channel:read",
            "asset:datacenter:read", "asset:datacenter:write", "asset:server:read", "asset:server:write",
            "monitor:metric:read", "monitor:metric:write", "monitor:alert:read", "monitor:alert:write", "monitor:alert:execute", "monitor:collect:execute",
            "outband:info:read", "outband:power:execute", "outband:kvm:execute", "outband:sel:read", "outband:sel:write",
            "audit:log:read", "audit:notification:execute",
            "autoops:task:read", "autoops:task:write", "autoops:task:execute",
            "knowledge:read", "knowledge:write",
        ]
        for c in operator_perms:
            await session.execute(insert(role_permissions).values(role_id=OPERATOR_ROLE_ID, permission_id=pm[c]))
        viewer_perms = [
            "system:user:read", "system:role:read", "system:config:read", "system:channel:read",
            "asset:datacenter:read", "asset:server:read",
            "monitor:metric:read", "monitor:alert:read",
            "outband:info:read", "outband:sel:read",
            "audit:log:read",
            "autoops:task:read",
            "knowledge:read",
        ]
        for c in viewer_perms:
            await session.execute(insert(role_permissions).values(role_id=VIEWER_ROLE_ID, permission_id=pm[c]))
        await session.flush()

        # --- 用户 ---
        session.add(User(id=ADMIN_ID, username="admin", email="admin@opsnexus.com", password_hash=pwd_ctx.hash("admin123"), full_name="系统管理员", department="信息技术部", is_superuser=True, user_type="owner", company="衡驭智能", title="运维总监", last_login_at=now - timedelta(hours=2)))
        session.add(User(id=OPERATOR_ID, username="zhangwei", email="zhangwei@opsnexus.com", password_hash=pwd_ctx.hash("ops123456"), full_name="张伟", department="运维部", user_type="provider", company="衡驭智能", title="高级运维工程师", last_login_at=now - timedelta(minutes=30)))
        session.add(User(id=VIEWER_ID, username="liming", email="liming@opsnexus.com", password_hash=pwd_ctx.hash("view123456"), full_name="李明", department="研发部", user_type="owner", company="衡驭智能", title="开发经理", last_login_at=now - timedelta(days=1)))
        await session.flush()
        await session.execute(insert(user_roles).values(user_id=ADMIN_ID, role_id=SUPERADMIN_ROLE_ID))
        await session.execute(insert(user_roles).values(user_id=OPERATOR_ID, role_id=OPERATOR_ROLE_ID))
        await session.execute(insert(user_roles).values(user_id=VIEWER_ID, role_id=VIEWER_ROLE_ID))
        await session.flush()

        # --- 数据中心 ---
        session.add(DataCenter(id=DC_BJ, name="北京亦庄数据中心", code="DC-BJ-YZ", location="北京市大兴区亦庄经济开发区科创十一街18号院", contact_name="王建国", contact_phone="010-82345678", description="主数据中心，承载核心业务系统"))
        session.add(DataCenter(id=DC_SH, name="上海浦东数据中心", code="DC-SH-PD", location="上海市浦东新区张江高科技园区碧波路690号", contact_name="陈志远", contact_phone="021-61234567", description="灾备数据中心，同步核心数据"))
        session.add(DataCenter(id=DC_GZ, name="广州天河数据中心", code="DC-GZ-TH", location="广州市天河区科韵路16号广州信息港", contact_name="黄海涛", contact_phone="020-83456789", description="华南区域数据中心"))
        await session.flush()

        # --- 机柜 ---
        for rid, dcid, name, code, loc in [
            (R_BJ_A01, DC_BJ, "A01", "BJ-A01", "A列01号"),
            (R_BJ_A02, DC_BJ, "A02", "BJ-A02", "A列02号"),
            (R_BJ_B01, DC_BJ, "B01", "BJ-B01", "B列01号"),
            (R_SH_A01, DC_SH, "A01", "SH-A01", "A列01号"),
            (R_SH_A02, DC_SH, "A02", "SH-A02", "A列02号"),
            (R_GZ_A01, DC_GZ, "A01", "GZ-A01", "A列01号"),
        ]:
            session.add(Rack(id=rid, data_center_id=dcid, name=name, code=code, location=loc, u_height=42))
        await session.flush()

        # --- 服务器 ---
        svrs = [
            {"id": _sid(1), "name": "BJ-DB-001", "model": "PowerEdge R750", "brand": "Dell", "status": "active", "rack_id": R_BJ_A01, "rack_position": 1, "rack_height": 2, "hostname": "db-master-01", "serial_number": "Dell-SN-20240101", "asset_tag": "AST-BJ-DB-001", "cpu_model": "Intel Xeon Gold 6348", "cpu_count": 2, "cpu_cores_per_socket": 28, "memory_gb": 512, "os_name": "CentOS", "os_version": "7.9", "bmc_ip": "10.0.1.101", "bmc_status": "online", "department": "数据库部", "owner_id": OPERATOR_ID},
            {"id": _sid(2), "name": "BJ-DB-002", "model": "PowerEdge R750", "brand": "Dell", "status": "active", "rack_id": R_BJ_A01, "rack_position": 3, "rack_height": 2, "hostname": "db-slave-01", "serial_number": "Dell-SN-20240102", "asset_tag": "AST-BJ-DB-002", "cpu_model": "Intel Xeon Gold 6348", "cpu_count": 2, "cpu_cores_per_socket": 28, "memory_gb": 512, "os_name": "CentOS", "os_version": "7.9", "bmc_ip": "10.0.1.102", "bmc_status": "online", "department": "数据库部", "owner_id": OPERATOR_ID},
            {"id": _sid(3), "name": "BJ-APP-001", "model": "ProLiant DL380 Gen11", "brand": "HPE", "status": "active", "rack_id": R_BJ_A01, "rack_position": 5, "rack_height": 2, "hostname": "app-server-01", "serial_number": "HPE-SN-20240201", "asset_tag": "AST-BJ-APP-001", "cpu_model": "Intel Xeon Platinum 8468", "cpu_count": 2, "cpu_cores_per_socket": 48, "memory_gb": 1024, "os_name": "Ubuntu", "os_version": "22.04 LTS", "bmc_ip": "10.0.1.201", "bmc_status": "online", "department": "应用部", "owner_id": OPERATOR_ID},
            {"id": _sid(4), "name": "BJ-APP-002", "model": "ProLiant DL380 Gen11", "brand": "HPE", "status": "active", "rack_id": R_BJ_A02, "rack_position": 1, "rack_height": 2, "hostname": "app-server-02", "serial_number": "HPE-SN-20240202", "asset_tag": "AST-BJ-APP-002", "cpu_model": "Intel Xeon Platinum 8468", "cpu_count": 2, "cpu_cores_per_socket": 48, "memory_gb": 1024, "os_name": "Ubuntu", "os_version": "22.04 LTS", "bmc_ip": "10.0.1.202", "bmc_status": "online", "department": "应用部", "owner_id": OPERATOR_ID},
            {"id": _sid(5), "name": "BJ-WEB-001", "model": "ThinkSystem SR650 V3", "brand": "Lenovo", "status": "active", "rack_id": R_BJ_A02, "rack_position": 3, "rack_height": 2, "hostname": "web-frontend-01", "serial_number": "Lenovo-SN-20240301", "asset_tag": "AST-BJ-WEB-001", "cpu_model": "Intel Xeon Silver 4410Y", "cpu_count": 2, "cpu_cores_per_socket": 12, "memory_gb": 256, "os_name": "Ubuntu", "os_version": "22.04 LTS", "bmc_ip": "10.0.1.301", "bmc_status": "online", "department": "前端组", "owner_id": OPERATOR_ID},
            {"id": _sid(6), "name": "BJ-WEB-002", "model": "ThinkSystem SR650 V3", "brand": "Lenovo", "status": "active", "rack_id": R_BJ_A02, "rack_position": 5, "rack_height": 2, "hostname": "web-frontend-02", "serial_number": "Lenovo-SN-20240302", "asset_tag": "AST-BJ-WEB-002", "cpu_model": "Intel Xeon Silver 4410Y", "cpu_count": 2, "cpu_cores_per_socket": 12, "memory_gb": 256, "os_name": "Ubuntu", "os_version": "22.04 LTS", "bmc_ip": "10.0.1.302", "bmc_status": "online", "department": "前端组", "owner_id": OPERATOR_ID},
            {"id": _sid(7), "name": "BJ-CACHE-001", "model": "FusionServer Pro 2288H V7", "brand": "Huawei", "status": "active", "rack_id": R_BJ_B01, "rack_position": 1, "rack_height": 2, "hostname": "cache-redis-01", "serial_number": "HW-SN-20240401", "asset_tag": "AST-BJ-CACHE-001", "cpu_model": "Intel Xeon Gold 5318Y", "cpu_count": 2, "cpu_cores_per_socket": 24, "memory_gb": 512, "os_name": "CentOS", "os_version": "7.9", "bmc_ip": "10.0.1.401", "bmc_status": "online", "department": "中间件部", "owner_id": OPERATOR_ID},
            {"id": _sid(8), "name": "BJ-MQ-001", "model": "FusionServer Pro 2288H V7", "brand": "Huawei", "status": "maintenance", "rack_id": R_BJ_B01, "rack_position": 3, "rack_height": 2, "hostname": "mq-rabbitmq-01", "serial_number": "HW-SN-20240402", "asset_tag": "AST-BJ-MQ-001", "cpu_model": "Intel Xeon Gold 5318Y", "cpu_count": 2, "cpu_cores_per_socket": 24, "memory_gb": 256, "os_name": "Ubuntu", "os_version": "22.04 LTS", "bmc_ip": "10.0.1.402", "bmc_status": "offline", "bmc_unreachable": True, "bmc_unreachable_since": now - timedelta(hours=6), "department": "中间件部", "owner_id": OPERATOR_ID},
            {"id": _sid(9), "name": "SH-DB-001", "model": "PowerEdge R750xs", "brand": "Dell", "status": "active", "rack_id": R_SH_A01, "rack_position": 1, "rack_height": 2, "hostname": "dr-db-master-01", "serial_number": "Dell-SN-20240501", "asset_tag": "AST-SH-DB-001", "cpu_model": "Intel Xeon Gold 6338", "cpu_count": 2, "cpu_cores_per_socket": 32, "memory_gb": 512, "os_name": "CentOS", "os_version": "7.9", "bmc_ip": "10.1.1.101", "bmc_status": "online", "department": "数据库部", "owner_id": OPERATOR_ID},
            {"id": _sid(10), "name": "SH-APP-001", "model": "ProLiant DL360 Gen11", "brand": "HPE", "status": "active", "rack_id": R_SH_A01, "rack_position": 3, "rack_height": 1, "hostname": "dr-app-server-01", "serial_number": "HPE-SN-20240601", "asset_tag": "AST-SH-APP-001", "cpu_model": "Intel Xeon Gold 6430", "cpu_count": 2, "cpu_cores_per_socket": 32, "memory_gb": 512, "os_name": "Ubuntu", "os_version": "22.04 LTS", "bmc_ip": "10.1.1.201", "bmc_status": "online", "department": "应用部", "owner_id": OPERATOR_ID},
            {"id": _sid(11), "name": "SH-BACKUP-001", "model": "ThinkSystem SR630 V3", "brand": "Lenovo", "status": "active", "rack_id": R_SH_A02, "rack_position": 1, "rack_height": 1, "hostname": "backup-server-01", "serial_number": "Lenovo-SN-20240701", "asset_tag": "AST-SH-BACKUP-001", "cpu_model": "Intel Xeon Silver 4314", "cpu_count": 2, "cpu_cores_per_socket": 16, "memory_gb": 256, "os_name": "CentOS", "os_version": "7.9", "bmc_ip": "10.1.1.301", "bmc_status": "online", "department": "备份组", "owner_id": OPERATOR_ID},
            {"id": _sid(12), "name": "GZ-APP-001", "model": "FusionServer Pro 2488H V7", "brand": "Huawei", "status": "active", "rack_id": R_GZ_A01, "rack_position": 1, "rack_height": 2, "hostname": "gz-app-server-01", "serial_number": "HW-SN-20240801", "asset_tag": "AST-GZ-APP-001", "cpu_model": "Intel Xeon Gold 6348", "cpu_count": 2, "cpu_cores_per_socket": 28, "memory_gb": 512, "os_name": "Ubuntu", "os_version": "22.04 LTS", "bmc_ip": "10.2.1.101", "bmc_status": "online", "department": "华南应用部", "owner_id": OPERATOR_ID},
            {"id": _sid(13), "name": "GZ-APP-002", "model": "FusionServer Pro 2488H V7", "brand": "Huawei", "status": "inactive", "rack_id": R_GZ_A01, "rack_position": 3, "rack_height": 2, "hostname": "gz-app-server-02", "serial_number": "HW-SN-20240802", "asset_tag": "AST-GZ-APP-002", "cpu_model": "Intel Xeon Gold 6348", "cpu_count": 2, "cpu_cores_per_socket": 28, "memory_gb": 512, "os_name": "Ubuntu", "os_version": "22.04 LTS", "bmc_ip": "10.2.1.102", "bmc_status": "unknown", "department": "华南应用部"},
        ]
        for s in svrs:
            session.add(Server(**s))
        await session.flush()

        # --- 监控指标 ---
        for i, (n, dn, u, mt) in enumerate([
            ("cpu_temperature_celsius", "CPU温度", "°C", "gauge"),
            ("cpu_usage_percent", "CPU使用率", "%", "gauge"),
            ("memory_usage_percent", "内存使用率", "%", "gauge"),
            ("disk_usage_percent", "磁盘使用率", "%", "gauge"),
            ("system_power_watts", "系统功耗", "W", "gauge"),
            ("fan_speed_rpm", "风扇转速", "RPM", "gauge"),
            ("nic_bandwidth_mbps", "网卡带宽", "Mbps", "counter"),
            ("bmc_uptime_seconds", "BMC运行时间", "s", "counter"),
        ]):
            session.add(MetricDefinition(id=uuid.UUID(f"40000000-0000-0000-0000-{i+1:012d}"), name=n, display_name=dn, unit=u, metric_type=mt, data_type="float", collection_method="bmc", default_interval=60))
        await session.flush()

        # --- 告警规则 ---
        rule_ids = []
        for i, (n, mn, c, t, s, d) in enumerate([
            ("CPU温度过高告警", "cpu_temperature_celsius", "gt", 85.0, "critical", "当CPU温度持续超过85°C时触发"),
            ("CPU使用率过高", "cpu_usage_percent", "gt", 90.0, "warning", "当CPU使用率持续5分钟超过90%时触发"),
            ("内存使用率过高", "memory_usage_percent", "gt", 90.0, "warning", "当内存使用率持续5分钟超过90%时触发"),
            ("磁盘使用率过高", "disk_usage_percent", "gt", 85.0, "warning", "当磁盘使用率持续10分钟超过85%时触发"),
            ("功耗异常告警", "system_power_watts", "gt", 800.0, "critical", "当系统功耗持续超过800W时触发"),
        ]):
            rid = uuid.UUID(f"50000000-0000-0000-0000-{i+1:012d}")
            rule_ids.append(rid)
            session.add(AlertRule(id=rid, name=n, metric_name=mn, condition=c, threshold=t, duration=60, severity=s, is_enabled=True, created_by=ADMIN_ID, description=d))
        await session.flush()

        # --- 告警事件 ---
        active_sids = [_sid(i) for i in range(1, 8)]
        ev_data = [
            ("CPU温度过高", "CPU温度已超过85°C阈值", "critical", "firing", 87.5),
            ("CPU使用率过高", "CPU使用率已超过90%阈值", "warning", "resolved", 93.2),
            ("内存使用率过高", "内存使用率已超过90%阈值", "warning", "acknowledged", 91.8),
            ("磁盘使用率过高", "磁盘使用率已超过85%阈值", "warning", "firing", 88.1),
            ("功耗异常", "系统功耗已超过800W阈值", "critical", "resolved", 856.0),
            ("CPU温度过高", "CPU温度已超过85°C阈值", "critical", "resolved", 86.3),
            ("内存使用率过高", "内存使用率已超过90%阈值", "warning", "firing", 92.3),
            ("CPU使用率过高", "CPU使用率已超过90%阈值", "warning", "acknowledged", 94.1),
        ]
        for i, (sum_, desc, sev, st, mv) in enumerate(ev_data):
            rid = rule_ids[i % len(rule_ids)]
            sid = active_sids[i % len(active_sids)]
            trig = now - timedelta(hours=i*3+1)
            session.add(AlertEvent(
                id=uuid.UUID(f"60000000-0000-0000-0000-{i+1:012d}"),
                rule_id=rid, server_id=sid, severity=sev, status=st,
                summary=sum_, description=desc, metric_value=mv,
                triggered_at=trig,
                resolved_at=trig + timedelta(minutes=15+i*5) if st == "resolved" else None,
                acknowledged_by=OPERATOR_ID if st == "acknowledged" else None,
                acknowledged_at=trig + timedelta(minutes=5) if st == "acknowledged" else None,
                notification_sent=st != "firing",
            ))
        await session.flush()

        # --- SEL日志 ---
        sel_data = [
            ("Temperature", "CPU0 Temp", "Upper Critical", "critical", "CPU0 温度超过上限阈值 85°C"),
            ("Fan", "System Fan 1", "Lower Critical", "warning", "系统风扇1转速低于最低阈值"),
            ("Voltage", "PSU1 Voltage", "Lower Critical", "critical", "电源1输出电压低于正常范围"),
            ("Memory", "DIMM_A1 ECC", "Uncorrectable Error", "critical", "DIMM_A1 检测到不可纠正ECC错误"),
            ("Drive", "Disk 0 SMART", "Predictive Failure", "warning", "磁盘0 SMART预测性故障"),
            ("Power Supply", "PSU2 Status", "Failure", "critical", "电源2故障"),
            ("Watchdog", "OS Watchdog", "Timeout", "critical", "操作系统看门狗超时"),
            ("System Board", "BMC Health", "Degraded", "warning", "BMC健康状态降级"),
            ("NIC", "NIC 1 Link", "Link Down", "warning", "网卡1链路断开"),
            ("PCIe", "PCIe Slot 1", "AER Error", "warning", "PCIe插槽1检测到AER错误"),
        ]
        for i, (st, sn, et, sev, desc) in enumerate(sel_data):
            sid = active_sids[i % len(active_sids)]
            ts = now - timedelta(hours=i*6+2)
            session.add(SELLog(
                id=uuid.UUID(f"70000000-0000-0000-0000-{i+1:012d}"),
                server_id=sid, record_id=i+1, timestamp=ts,
                sensor_type=st, sensor_name=sn, event_type=et, severity=sev, description=desc,
                is_acknowledged=i < 5, acknowledged_by=OPERATOR_ID if i < 5 else None,
                acknowledged_at=ts + timedelta(minutes=10) if i < 5 else None,
            ))
        await session.flush()

        # --- 固件清单 ---
        fw_data = [
            (_sid(1), "BIOS", "2.16.0", "2.18.1", "update_available"),
            (_sid(1), "iDRAC", "7.10.45.00", "7.10.50.00", "update_available"),
            (_sid(2), "BIOS", "2.18.1", "2.18.1", "up_to_date"),
            (_sid(2), "iDRAC", "7.10.50.00", "7.10.50.00", "up_to_date"),
            (_sid(3), "BIOS", "1.58", "1.60", "update_available"),
            (_sid(3), "iLO", "2.83", "2.85", "update_available"),
            (_sid(4), "BIOS", "1.60", "1.60", "up_to_date"),
            (_sid(4), "iLO", "2.85", "2.85", "up_to_date"),
            (_sid(5), "XCC", "4.10.1", "4.10.2a", "update_available"),
            (_sid(5), "UEFI", "UEFI-3.19", "UEFI-3.20", "update_available"),
            (_sid(6), "XCC", "4.10.2a", "4.10.2a", "up_to_date"),
            (_sid(7), "iBMC", "6.32.2.10", "6.32.3.10", "update_available"),
            (_sid(7), "BIOS", "1.96", "1.97", "update_available"),
            (_sid(9), "BIOS", "2.18.1", "2.18.1", "up_to_date"),
            (_sid(10), "iLO", "2.85", "2.85", "up_to_date"),
            (_sid(12), "iBMC", "6.32.3.10", "6.32.3.10", "up_to_date"),
        ]
        for i, (sid, comp, cv, av, st) in enumerate(fw_data):
            session.add(FirmwareInventory(
                id=uuid.UUID(f"80000000-0000-0000-0000-{i+1:012d}"),
                server_id=sid, component=comp, current_version=cv, available_version=av, update_status=st,
                last_checked_at=now - timedelta(hours=i),
            ))
        await session.flush()

        # --- KVM会话 ---
        session.add(KVMSession(id=uuid.UUID(f"90000000-0000-0000-0000-000000000001"), server_id=_sid(1), user_id=OPERATOR_ID, proxy_token="kvm-token-active-001", status="active", started_at=now - timedelta(minutes=15), expires_at=now + timedelta(hours=1), client_ip="192.168.1.100"))
        session.add(KVMSession(id=uuid.UUID(f"90000000-0000-0000-0000-000000000002"), server_id=_sid(3), user_id=OPERATOR_ID, proxy_token="kvm-token-expired-001", status="expired", started_at=now - timedelta(hours=3), expires_at=now - timedelta(hours=2), ended_at=now - timedelta(hours=2), client_ip="192.168.1.100"))
        session.add(KVMSession(id=uuid.UUID(f"90000000-0000-0000-0000-000000000003"), server_id=_sid(9), user_id=ADMIN_ID, proxy_token="kvm-token-term-001", status="terminated", started_at=now - timedelta(days=1), expires_at=now - timedelta(hours=20), ended_at=now - timedelta(hours=22), client_ip="192.168.1.50"))
        await session.flush()

        # --- 系统配置 ---
        for i, (k, v, vt, d) in enumerate([
            ("system.name", "OpsNexus 运维管理平台", "string", "系统名称"),
            ("system.version", "0.1.1", "string", "系统版本"),
            ("monitor.collect_interval", "60", "int", "监控数据采集间隔(秒)"),
            ("monitor.retention_days", "90", "int", "监控数据保留天数"),
            ("alert.notification_enabled", "true", "bool", "是否启用告警通知"),
            ("audit.retention_days", "365", "int", "审计日志保留天数"),
        ]):
            session.add(SystemConfig(id=uuid.UUID(f"a0000000-0000-0000-0000-{i+1:012d}"), key=k, value=v, value_type=vt, description=d))
        await session.flush()

        # --- 通知渠道 ---
        ch1 = uuid.UUID(f"b0000000-0000-0000-0000-000000000001")
        ch2 = uuid.UUID(f"b0000000-0000-0000-0000-000000000002")
        ch3 = uuid.UUID(f"b0000000-0000-0000-0000-000000000003")
        session.add(NotificationChannel(id=ch1, name="运维邮件组", channel_type="email", config='{"recipients": ["ops@opsnexus.com"], "smtp_host": "smtp.opsnexus.com", "smtp_port": 587}', is_enabled=True))
        session.add(NotificationChannel(id=ch2, name="钉钉告警群", channel_type="dingtalk", config='{"webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx"}', is_enabled=True))
        session.add(NotificationChannel(id=ch3, name="企业微信通知", channel_type="wecom", config='{"webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"}', is_enabled=False))
        await session.flush()

        # --- 审计日志 ---
        audit_data = [
            ("admin", "login", "system", None, None, "用户登录系统", "192.168.1.50"),
            ("admin", "create", "server", str(_sid(1)), "BJ-DB-001", "创建服务器资产", "192.168.1.50"),
            ("admin", "create", "server", str(_sid(3)), "BJ-APP-001", "创建服务器资产", "192.168.1.50"),
            ("zhangwei", "login", "system", None, None, "用户登录系统", "192.168.1.100"),
            ("zhangwei", "update", "server", str(_sid(8)), "BJ-MQ-001", "更新服务器状态为维护中", "192.168.1.100"),
            ("zhangwei", "execute", "kvm", str(_sid(1)), "BJ-DB-001", "发起KVM远程控制会话", "192.168.1.100"),
            ("admin", "create", "alert_rule", str(rule_ids[0]), "CPU温度过高告警", "创建告警规则", "192.168.1.50"),
            ("zhangwei", "acknowledge", "alert_event", None, "内存使用率过高", "确认告警事件", "192.168.1.100"),
            ("admin", "update", "system_config", None, "monitor.collect_interval", "修改监控采集间隔", "192.168.1.50"),
            ("liming", "login", "system", None, None, "用户登录系统", "192.168.1.200"),
            ("zhangwei", "query", "sel_log", str(_sid(1)), "BJ-DB-001", "查询SEL系统事件日志", "192.168.1.100"),
            ("admin", "create", "notification_channel", str(ch1), "运维邮件组", "创建通知渠道", "192.168.1.50"),
            ("zhangwei", "update", "firmware", str(_sid(1)), "BJ-DB-001", "检查固件更新", "192.168.1.100"),
            ("admin", "create", "user", str(VIEWER_ID), "liming", "创建用户", "192.168.1.50"),
            ("zhangwei", "export", "audit_log", None, None, "导出审计日志", "192.168.1.100"),
        ]
        for i, (u, a, rt, rid, rn, d, ip) in enumerate(audit_data):
            uid = ADMIN_ID if u == "admin" else (OPERATOR_ID if u == "zhangwei" else VIEWER_ID)
            session.add(AuditLog(
                id=uuid.UUID(f"c0000000-0000-0000-0000-{i+1:012d}"),
                user_id=uid, username=u, action=a, resource_type=rt,
                resource_id=rid, resource_name=rn, detail={"message": d},
                ip_address=ip, status="success", created_at=now - timedelta(hours=len(audit_data)-i),
            ))
        await session.flush()

        # --- 通知日志 ---
        for i, (cid, ct, r, s, c, st) in enumerate([
            (ch1, "email", "ops@opsnexus.com", "告警：BJ-DB-001 CPU温度过高", "服务器 BJ-DB-001 CPU温度已超过85°C阈值，当前值87.5°C", "sent"),
            (ch2, "dingtalk", "运维告警群", "告警：BJ-APP-001 内存使用率过高", "服务器 BJ-APP-001 内存使用率已超过90%阈值，当前值92.3%", "sent"),
            (ch1, "email", "ops@opsnexus.com", "告警：BJ-WEB-001 磁盘使用率过高", "服务器 BJ-WEB-001 磁盘使用率已超过85%阈值，当前值88.1%", "sent"),
            (ch2, "dingtalk", "运维告警群", "告警恢复：BJ-DB-001 CPU温度恢复正常", "服务器 BJ-DB-001 CPU温度已恢复至正常范围", "sent"),
        ]):
            session.add(NotificationLog(
                id=uuid.UUID(f"d0000000-0000-0000-0000-{i+1:012d}"),
                channel_id=cid, channel_type=ct, recipient=r, subject=s, content=c, status=st,
                sent_at=now - timedelta(hours=len([1,2,3,4])-i),
            ))
        await session.flush()

        # --- 对话和消息 ---
        conv1 = uuid.UUID(f"e0000000-0000-0000-0000-000000000001")
        conv2 = uuid.UUID(f"e0000000-0000-0000-0000-000000000002")
        conv3 = uuid.UUID(f"e0000000-0000-0000-0000-000000000003")
        session.add(Conversation(id=conv1, user_id=OPERATOR_ID, title="Dell R750 iDRAC 告警排查", created_at=now - timedelta(days=2)))
        session.add(Conversation(id=conv2, user_id=OPERATOR_ID, title="HPE DL380 固件升级方案", created_at=now - timedelta(days=1)))
        session.add(Conversation(id=conv3, user_id=ADMIN_ID, title="华为2288H iBMC 远程管理问题", created_at=now - timedelta(hours=6)))
        await session.flush()

        msgs = [
            (conv1, "user", "Dell PowerEdge R750 的 iDRAC 报 E1006 告警，BMC通信异常，怎么处理？", "sel_query", "Dell", None),
            (conv1, "assistant", "根据 Dell SEL 事件码 E1006 的定义，该告警表示主板 BMC 通信异常，iDRAC 可能无法正常管理。\n\n**建议操作：**\n1. 重启 iDRAC 模块：通过 racadm racreset 命令\n2. 检查 iDRAC 固件版本，建议升级至 7.10.50.00\n3. 如问题持续，检查 iDRAC 网络连接和电源供应\n\n**参考来源：** Dell PowerEdge R750 iDRAC User Guide", None, "Dell", 1200),
            (conv2, "user", "HPE ProLiant DL380 Gen11 需要升级 iLO 固件，当前版本2.83，有什么注意事项？", "firmware_query", "HPE", None),
            (conv2, "assistant", "HPE ProLiant DL380 Gen11 的 iLO 固件可从 2.83 升级至 2.85。\n\n**升级注意事项：**\n1. 升级前确保服务器不在业务高峰期，iLO 重启期间远程管理功能会短暂中断\n2. 建议通过 iLO Web 界面或 SUM (Smart Update Manager) 进行升级\n3. 升级过程中不要断电或重启服务器\n4. 升级完成后建议执行 iLO 重置并验证所有功能正常\n\n**版本 2.85 更新内容：**\n- 修复 iLO 远程控制台断连问题\n- 增强安全认证机制", None, "HPE", 980),
            (conv3, "user", "华为 FusionServer 2288H V7 的 iBMC 报 HW4007 告警，管理芯片异常，带外管理不可用怎么办？", "sel_query", "Huawei", None),
            (conv3, "assistant", "根据华为 SEL 事件码 HW4007，iBMC 管理芯片异常导致带外管理不可用。\n\n**紧急处理步骤：**\n1. 通过 IPMI 命令尝试重置 iBMC：ipmitool mc reset cold\n2. 检查 iBMC 固件版本，当前最新版本为 6.32.3.10\n3. 如重置无效，尝试通过 BIOS 设置重置 BMC 配置\n4. 确认 iBMC 网口指示灯状态，排除物理连接问题\n\n**注意：** iBMC 异常期间无法进行远程开关机、KVM、虚拟媒体等操作，需现场处理", None, "Huawei", 1500),
        ]
        for i, (cid, role, content, qt, brand, latency) in enumerate(msgs):
            session.add(ConversationMessage(
                id=uuid.UUID(f"f0000000-0000-0000-0000-{i+1:012d}"),
                conversation_id=cid, role=role, content=content,
                query_type=qt, brand=brand, latency_ms=latency,
                sources=[{"title": f"{brand} 技术文档", "type": "document", "brand": brand}] if role == "assistant" else None,
                created_at=now - timedelta(days=2, hours=i),
            ))
        await session.flush()

        # --- 知识收藏 ---
        session.add(KnowledgeFavorite(id=uuid.UUID(f"ea000000-0000-0000-0000-000000000001"), user_id=OPERATOR_ID, message_id=uuid.UUID(f"f0000000-0000-0000-0000-000000000002"), title="Dell iDRAC E1006 告警处理方案", content="重启 iDRAC 模块（racadm racreset），检查固件版本并升级至 7.10.50.00", source_type="conversation", brand="Dell"))
        session.add(KnowledgeFavorite(id=uuid.UUID(f"ea000000-0000-0000-0000-000000000002"), user_id=OPERATOR_ID, message_id=uuid.UUID(f"f0000000-0000-0000-0000-000000000004"), title="HPE iLO 固件升级注意事项", content="升级前确保非业务高峰期，通过 iLO Web 或 SUM 升级，升级过程不断电", source_type="conversation", brand="HPE"))
        session.add(KnowledgeFavorite(id=uuid.UUID(f"ea000000-0000-0000-0000-000000000003"), user_id=ADMIN_ID, message_id=uuid.UUID(f"f0000000-0000-0000-0000-000000000006"), title="华为 iBMC HW4007 故障处理", content="通过 IPMI 重置 iBMC，检查固件版本，确认网口物理连接", source_type="conversation", brand="Huawei"))
        await session.flush()

        # --- 知识库种子 ---
        await seed_knowledge_data(session)

        await session.commit()
        print("种子数据插入完成！")


if __name__ == "__main__":
    asyncio.run(seed_all())
