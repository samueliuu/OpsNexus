#!/usr/bin/env python3
"""Initialize database with seed data."""

import asyncio
import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash
from app.modules.monitor.models import MetricDefinition
from app.modules.system.models import Permission, Role, User


# Seed data
SEED_ROLES = [
    {"name": "超级管理员", "code": "super_admin", "is_builtin": True},
    {"name": "运维管理员", "code": "ops_admin", "is_builtin": True},
    {"name": "运维工程师", "code": "ops_engineer", "is_builtin": True},
    {"name": "只读用户", "code": "viewer", "is_builtin": True},
    {"name": "审计员", "code": "auditor", "is_builtin": True},
]

SEED_PERMISSIONS = [
    # System permissions
    {"code": "system:user:read", "name": "查看用户", "resource": "system", "action": "read"},
    {"code": "system:user:write", "name": "管理用户", "resource": "system", "action": "write"},
    {"code": "system:role:read", "name": "查看角色", "resource": "system", "action": "read"},
    {"code": "system:role:write", "name": "管理角色", "resource": "system", "action": "write"},
    {"code": "system:config:read", "name": "查看配置", "resource": "system", "action": "read"},
    {"code": "system:config:write", "name": "管理配置", "resource": "system", "action": "write"},
    {"code": "system:channel:read", "name": "查看通知渠道", "resource": "system", "action": "read"},
    {"code": "system:channel:write", "name": "管理通知渠道", "resource": "system", "action": "write"},
    # Asset permissions
    {"code": "asset:datacenter:read", "name": "查看数据中心", "resource": "asset", "action": "read"},
    {"code": "asset:datacenter:write", "name": "管理数据中心", "resource": "asset", "action": "write"},
    {"code": "asset:server:read", "name": "查看服务器", "resource": "asset", "action": "read"},
    {"code": "asset:server:write", "name": "管理服务器", "resource": "asset", "action": "write"},
    # Monitor permissions
    {"code": "monitor:metric:read", "name": "查看指标", "resource": "monitor", "action": "read"},
    {"code": "monitor:metric:write", "name": "管理指标", "resource": "monitor", "action": "write"},
    {"code": "monitor:alert:read", "name": "查看告警", "resource": "monitor", "action": "read"},
    {"code": "monitor:alert:write", "name": "管理告警", "resource": "monitor", "action": "write"},
    {"code": "monitor:alert:execute", "name": "告警操作", "resource": "monitor", "action": "execute"},
    {"code": "monitor:collect:execute", "name": "执行采集", "resource": "monitor", "action": "execute"},
    # OutBand permissions
    {"code": "outband:info:read", "name": "查看带外信息", "resource": "outband", "action": "read"},
    {"code": "outband:power:execute", "name": "电源控制", "resource": "outband", "action": "execute"},
    {"code": "outband:kvm:execute", "name": "KVM 控制台", "resource": "outband", "action": "execute"},
    {"code": "outband:firmware:read", "name": "查看固件", "resource": "outband", "action": "read"},
    {"code": "outband:sel:read", "name": "查看SEL日志", "resource": "outband", "action": "read"},
    {"code": "outband:sel:write", "name": "管理SEL日志", "resource": "outband", "action": "write"},
    # AutoOps permissions
    {"code": "autoops:task:read", "name": "查看任务", "resource": "autoops", "action": "read"},
    {"code": "autoops:task:write", "name": "管理任务", "resource": "autoops", "action": "write"},
    {"code": "autoops:task:execute", "name": "执行任务", "resource": "autoops", "action": "execute"},
    {"code": "autoops:task:approve", "name": "审批任务", "resource": "autoops", "action": "approve"},
    # Audit permissions
    {"code": "audit:log:read", "name": "查看审计日志", "resource": "audit", "action": "read"},
    {"code": "audit:log:write", "name": "管理审计日志", "resource": "audit", "action": "write"},
    {"code": "audit:notification:execute", "name": "发送通知", "resource": "audit", "action": "execute"},
]

# Role-Permission mapping
ROLE_PERMISSIONS = {
    "super_admin": [p["code"] for p in SEED_PERMISSIONS],
    "ops_admin": [
        "system:config:read",
        "asset:datacenter:read",
        "asset:datacenter:write",
        "asset:server:read",
        "asset:server:write",
        "monitor:metric:read",
        "monitor:metric:write",
        "monitor:alert:read",
        "monitor:alert:write",
        "monitor:alert:execute",
        "monitor:collect:execute",
        "outband:info:read",
        "outband:power:execute",
        "outband:kvm:execute",
        "outband:firmware:read",
        "outband:sel:read",
        "outband:sel:write",
        "autoops:task:read",
        "autoops:task:write",
        "autoops:task:execute",
        "audit:log:read",
    ],
    "ops_engineer": [
        "asset:server:read",
        "monitor:metric:read",
        "monitor:alert:read",
        "monitor:alert:execute",
        "outband:info:read",
        "outband:power:execute",
        "outband:sel:read",
        "autoops:task:read",
        "autoops:task:execute",
    ],
    "viewer": [
        "asset:server:read",
        "monitor:metric:read",
        "monitor:alert:read",
        "outband:info:read",
        "outband:sel:read",
    ],
    "auditor": [
        "audit:log:read",
        "audit:log:write",
        "audit:notification:execute",
        "asset:server:read",
        "monitor:alert:read",
    ],
}


async def seed_permissions(session: AsyncSessionLocal):
    """Seed permissions."""
    for perm_data in SEED_PERMISSIONS:
        result = await session.execute(
            select(Permission).where(Permission.code == perm_data["code"])
        )
        if result.scalar_one_or_none() is None:
            permission = Permission(
                id=uuid.uuid4(),
                code=perm_data["code"],
                name=perm_data["name"],
                resource=perm_data["resource"],
                action=perm_data["action"],
                is_builtin=True,
            )
            session.add(permission)
            print(f"Created permission: {perm_data['code']}")
    await session.commit()


async def seed_roles(session: AsyncSessionLocal):
    """Seed roles with permissions."""
    # Get all permissions
    result = await session.execute(select(Permission))
    permissions = {p.code: p for p in result.scalars().all()}

    for role_data in SEED_ROLES:
        result = await session.execute(
            select(Role).where(Role.code == role_data["code"])
        )
        role = result.scalar_one_or_none()

        if role is None:
            role = Role(
                id=uuid.uuid4(),
                name=role_data["name"],
                code=role_data["code"],
                is_builtin=role_data["is_builtin"],
            )
            session.add(role)
            await session.flush()
            print(f"Created role: {role_data['code']}")

        # Assign permissions
        role_code = role_data["code"]
        if role_code in ROLE_PERMISSIONS:
            for perm_code in ROLE_PERMISSIONS[role_code]:
                if perm_code in permissions:
                    if permissions[perm_code] not in role.permissions:
                        role.permissions.append(permissions[perm_code])

    await session.commit()


async def seed_admin_user(session: AsyncSessionLocal):
    """Seed admin user."""
    result = await session.execute(
        select(User).where(User.username == "admin")
    )
    if result.scalar_one_or_none() is None:
        # Get super_admin role
        result = await session.execute(
            select(Role).where(Role.code == "super_admin")
        )
        super_admin_role = result.scalar_one()

        admin_user = User(
            id=uuid.uuid4(),
            username="admin",
            email="admin@opsnexus.local",
            password_hash=get_password_hash("admin123"),
            full_name="Administrator",
            is_active=True,
            is_superuser=True,
        )
        admin_user.roles.append(super_admin_role)
        session.add(admin_user)
        await session.commit()
        print("Created admin user: admin / admin123")
        print("WARNING: Please change the default password after first login!")


SEED_METRICS = [
    {"name": "cpu_temperature_celsius", "display_name": "CPU 温度", "description": "CPU 传感器温度读数", "unit": "°C", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 60},
    {"name": "cpu_usage_percent", "display_name": "CPU 使用率", "description": "CPU 利用率百分比", "unit": "%", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 60},
    {"name": "memory_usage_percent", "display_name": "内存使用率", "description": "内存利用率百分比", "unit": "%", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 60},
    {"name": "disk_usage_percent", "display_name": "磁盘使用率", "description": "磁盘利用率百分比", "unit": "%", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 120},
    {"name": "power_consumption_watts", "display_name": "功耗", "description": "服务器总功耗", "unit": "W", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 60},
    {"name": "fan_speed_rpm", "display_name": "风扇转速", "description": "风扇转速", "unit": "RPM", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 60},
    {"name": "fan_speed_rpm_avg", "display_name": "平均风扇转速", "description": "所有风扇平均转速", "unit": "RPM", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 60},
    {"name": "voltage_volts", "display_name": "电压", "description": "电压传感器读数", "unit": "V", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 120},
    {"name": "current_amps", "display_name": "电流", "description": "电流传感器读数", "unit": "A", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 120},
    {"name": "power_watts", "display_name": "功率", "description": "功率传感器读数", "unit": "W", "metric_type": "gauge", "data_type": "float", "collection_method": "bmc", "default_interval": 60},
    {"name": "bmc_uptime_seconds", "display_name": "BMC 运行时间", "description": "BMC 启动后运行秒数", "unit": "s", "metric_type": "counter", "data_type": "int", "collection_method": "bmc", "default_interval": 300},
    {"name": "server_power_state", "display_name": "服务器电源状态", "description": "服务器电源状态 (1=on, 0=off)", "unit": "", "metric_type": "gauge", "data_type": "int", "collection_method": "bmc", "default_interval": 60},
]


async def seed_metric_definitions(session: AsyncSessionLocal):
    """Seed metric definitions."""
    for metric_data in SEED_METRICS:
        result = await session.execute(
            select(MetricDefinition).where(MetricDefinition.name == metric_data["name"])
        )
        if result.scalar_one_or_none() is None:
            metric = MetricDefinition(
                id=uuid.uuid4(),
                labels=["server_id", "sensor_name"],
                is_active=True,
                **metric_data,
            )
            session.add(metric)
            print(f"Created metric definition: {metric_data['name']}")
    await session.commit()


async def main():
    """Main initialization function."""
    print("Initializing database...")
    await init_db()
    print("Database initialized.")

    async with AsyncSessionLocal() as session:
        print("Seeding permissions...")
        await seed_permissions(session)

        print("Seeding roles...")
        await seed_roles(session)

        print("Seeding admin user...")
        await seed_admin_user(session)

        print("Seeding metric definitions...")
        await seed_metric_definitions(session)

    print("Database initialization completed!")


if __name__ == "__main__":
    asyncio.run(main())
