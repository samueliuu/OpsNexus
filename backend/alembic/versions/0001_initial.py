"""Initial migration

Revision ID: 0001
Revises:
Create Date: 2026-04-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE kvm_status_enum AS ENUM ('active', 'expired', 'terminated')")
    op.execute("CREATE TYPE upload_status_enum AS ENUM ('pending', 'uploading', 'completed', 'verified', 'failed')")
    op.execute("CREATE TYPE key_status_enum AS ENUM ('active', 'rotating', 'deprecated')")

    # System module tables
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(64), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(128), nullable=True),
        sa.Column('phone', sa.String(32), nullable=True),
        sa.Column('department', sa.String(64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_username', 'users', ['username'])

    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('code', sa.String(64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('data_scope', sa.String(32), nullable=False, server_default='all'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_roles_code', 'roles', ['code'])

    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(128), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('resource', sa.String(64), nullable=False),
        sa.Column('action', sa.String(32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_permissions_code', 'permissions', ['code'])

    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )

    op.create_table(
        'role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    op.create_table(
        'system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(128), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(32), nullable=False, server_default='string'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index('ix_system_configs_key', 'system_configs', ['key'])

    op.create_table(
        'notification_channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('channel_type', sa.String(32), nullable=False),
        sa.Column('config', sa.Text(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Asset module tables
    op.create_table(
        'data_centers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('code', sa.String(64), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('contact_name', sa.String(64), nullable=True),
        sa.Column('contact_phone', sa.String(32), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    op.create_table(
        'racks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data_center_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('code', sa.String(64), nullable=False),
        sa.Column('location', sa.String(128), nullable=True),
        sa.Column('u_height', sa.Integer(), nullable=False, server_default='42'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['data_center_id'], ['data_centers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_racks_code', 'racks', ['code'])

    op.create_table(
        'servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rack_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('hostname', sa.String(128), nullable=True),
        sa.Column('serial_number', sa.String(64), nullable=True),
        sa.Column('asset_tag', sa.String(64), nullable=True),
        sa.Column('brand', sa.String(32), nullable=False),
        sa.Column('model', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='active'),
        sa.Column('server_type', sa.String(32), nullable=False, server_default='physical'),
        sa.Column('cpu_model', sa.String(128), nullable=True),
        sa.Column('cpu_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cpu_cores_per_socket', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('memory_gb', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('disk_info', postgresql.JSON(), nullable=True),
        sa.Column('network_interfaces', postgresql.JSON(), nullable=True),
        sa.Column('os_name', sa.String(64), nullable=True),
        sa.Column('os_version', sa.String(64), nullable=True),
        sa.Column('bmc_ip', sa.String(64), nullable=True),
        sa.Column('bmc_mac', sa.String(32), nullable=True),
        sa.Column('bmc_status', sa.String(32), nullable=False, server_default='unknown'),
        sa.Column('bmc_unreachable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('bmc_unreachable_since', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rack_position', sa.Integer(), nullable=True),
        sa.Column('rack_height', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department', sa.String(64), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['rack_id'], ['racks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname'),
        sa.UniqueConstraint('asset_tag')
    )
    op.create_index('ix_servers_brand', 'servers', ['brand'])
    op.create_index('ix_servers_status', 'servers', ['status'])
    op.create_index('ix_servers_bmc_ip', 'servers', ['bmc_ip'])
    op.create_index('ix_servers_serial_number', 'servers', ['serial_number'])

    op.create_table(
        'bmc_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(64), nullable=False),
        sa.Column('encrypted_password', sa.Text(), nullable=False),
        sa.Column('encryption_key_id', sa.String(64), nullable=False),
        sa.Column('protocol', sa.String(16), nullable=False, server_default='redfish'),
        sa.Column('port', sa.Integer(), nullable=False, server_default='443'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('server_id')
    )

    # Monitor module tables
    op.create_table(
        'metric_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('display_name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('unit', sa.String(32), nullable=True),
        sa.Column('metric_type', sa.String(32), nullable=False),
        sa.Column('data_type', sa.String(32), nullable=False, server_default='float'),
        sa.Column('labels', postgresql.JSON(), nullable=True),
        sa.Column('collection_method', sa.String(32), nullable=False, server_default='bmc'),
        sa.Column('default_interval', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_metric_definitions_name', 'metric_definitions', ['name'])

    # TimescaleDB hypertable for metric data
    op.create_table(
        'metric_data',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_name', sa.String(64), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('labels', postgresql.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'server_id', 'metric_name')
    )
    # Convert to hypertable (will be done manually or in app startup)

    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metric_name', sa.String(64), nullable=False),
        sa.Column('condition', sa.String(16), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('severity', sa.String(16), nullable=False, server_default='warning'),
        sa.Column('target_filter', postgresql.JSON(), nullable=True),
        sa.Column('notification_channels', postgresql.JSON(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_rules_metric_name', 'alert_rules', ['metric_name'])

    op.create_table(
        'alert_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='firing'),
        sa.Column('summary', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notification_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_events_status', 'alert_events', ['status'])

    # OutBand module tables
    op.create_table(
        'sel_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sensor_type', sa.String(64), nullable=False),
        sa.Column('sensor_name', sa.String(128), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('raw_data', postgresql.JSON(), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sel_logs_server_id', 'sel_logs', ['server_id'])
    op.create_index('ix_sel_logs_timestamp', 'sel_logs', ['timestamp'])

    op.create_table(
        'firmware_inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('component', sa.String(64), nullable=False),
        sa.Column('component_id', sa.String(64), nullable=True),
        sa.Column('current_version', sa.String(64), nullable=False),
        sa.Column('available_version', sa.String(64), nullable=True),
        sa.Column('update_status', sa.String(32), nullable=False, server_default='up_to_date'),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_firmware_inventory_server_id', 'firmware_inventory', ['server_id'])

    op.create_table(
        'kvm_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('proxy_token', sa.String(128), nullable=False),
        sa.Column('status', sa.Enum('active', 'expired', 'terminated', name='kvm_status_enum'), nullable=False, server_default='active'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('client_ip', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('proxy_token')
    )
    op.create_index('ix_kvm_sessions_server_id', 'kvm_sessions', ['server_id'])

    # AutoOps module tables
    op.create_table(
        'task_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(32), nullable=False),
        sa.Column('target_filter', postgresql.JSON(), nullable=False),
        sa.Column('steps', postgresql.JSON(), nullable=False),
        sa.Column('parameters', postgresql.JSON(), nullable=True),
        sa.Column('schedule', sa.String(64), nullable=True),
        sa.Column('is_scheduled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approver_roles', postgresql.JSON(), nullable=True),
        sa.Column('retry_policy', postgresql.JSON(), nullable=False, server_default='{"max_retries": 3, "retry_delay_seconds": 60}'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='3600'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_definitions_task_type', 'task_definitions', ['task_type'])

    op.create_table(
        'task_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_def_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('trigger_type', sa.String(16), nullable=False, server_default='manual'),
        sa.Column('parameters', postgresql.JSON(), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['task_def_id'], ['task_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_instances_status', 'task_instances', ['status'])

    op.create_table(
        'task_step_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(128), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['task_instance_id'], ['task_instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'firmware_packages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('brand', sa.String(32), nullable=False),
        sa.Column('component', sa.String(64), nullable=False),
        sa.Column('version', sa.String(64), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('minio_bucket', sa.String(64), nullable=False),
        sa.Column('minio_key', sa.String(512), nullable=False),
        sa.Column('upload_status', sa.Enum('pending', 'uploading', 'completed', 'verified', 'failed', name='upload_status_enum'), nullable=False, server_default='pending'),
        sa.Column('supported_models', postgresql.JSON(), nullable=True),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_firmware_packages_brand', 'firmware_packages', ['brand'])

    op.create_table(
        'inspection_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_def_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('schedule', sa.String(64), nullable=False),
        sa.Column('target_filter', postgresql.JSON(), nullable=False),
        sa.Column('check_items', postgresql.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['task_def_id'], ['task_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_def_id')
    )

    # Audit module tables
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('username', sa.String(64), nullable=True),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('resource_type', sa.String(64), nullable=False),
        sa.Column('resource_id', sa.String(64), nullable=True),
        sa.Column('resource_name', sa.String(128), nullable=True),
        sa.Column('detail', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('request_id', sa.String(64), nullable=True),
        sa.Column('status', sa.String(16), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    op.create_table(
        'notification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_type', sa.String(32), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('related_alert_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['channel_id'], ['notification_channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_alert_id'], ['alert_events.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('notification_logs')
    op.drop_table('audit_logs')
    op.drop_table('inspection_policies')
    op.drop_table('firmware_packages')
    op.drop_table('task_step_logs')
    op.drop_table('task_instances')
    op.drop_table('task_definitions')
    op.drop_table('kvm_sessions')
    op.drop_table('firmware_inventory')
    op.drop_table('sel_logs')
    op.drop_table('alert_events')
    op.drop_table('alert_rules')
    op.drop_table('metric_data')
    op.drop_table('metric_definitions')
    op.drop_table('bmc_credentials')
    op.drop_table('servers')
    op.drop_table('racks')
    op.drop_table('data_centers')
    op.drop_table('notification_channels')
    op.drop_table('system_configs')
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS upload_status_enum')
    op.execute('DROP TYPE IF EXISTS kvm_status_enum')
    op.execute('DROP TYPE IF EXISTS key_status_enum')
