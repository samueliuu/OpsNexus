import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import EventTypes, publish_event
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger
from app.modules.audit.models import AuditLog, NotificationLog
from app.modules.audit.repository import AuditLogRepository, NotificationLogRepository
from app.modules.audit.schemas import (
    AuditLogCreate,
    AuditLogStatsResponse,
    NotificationStatsResponse,
)
from app.modules.system.models import NotificationChannel

logger = get_logger(__name__)


class AuditLogService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuditLogRepository(session)

    async def create_log(self, data: AuditLogCreate) -> AuditLog:
        log = await self.repo.create(**data.model_dump())
        await publish_event(EventTypes.AUDIT_LOG_CREATED, {
            "log_id": str(log.id),
            "action": log.action,
            "resource_type": log.resource_type,
            "username": log.username,
            "status": log.status,
        })
        return log

    async def create_log_from_request(
        self,
        user_id: Optional[UUID],
        username: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        detail: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> AuditLog:
        return await self.repo.create(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            detail=detail,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
        )

    async def get_by_id(self, log_id: UUID) -> AuditLog:
        log = await self.repo.get_by_id(log_id)
        if not log:
            raise NotFoundException("AuditLog", str(log_id))
        return log

    async def list_all(self, **kwargs) -> Tuple[List[AuditLog], int]:
        return await self.repo.list_all(**kwargs)

    async def get_stats(self, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> AuditLogStatsResponse:
        stats = await self.repo.get_stats(start_time, end_time)
        return AuditLogStatsResponse(**stats)

    async def cleanup(self, retention_days: int = 180) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        return await self.repo.delete_before(cutoff)


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationLogRepository(session)

    async def send_notification(
        self,
        channel_ids: List[UUID],
        subject: Optional[str],
        content: str,
        recipients: Optional[List[str]] = None,
        related_alert_id: Optional[UUID] = None,
    ) -> List[NotificationLog]:
        results = []
        for channel_id in channel_ids:
            channel_result = await self.session.execute(
                select(NotificationChannel).where(NotificationChannel.id == channel_id)
            )
            channel = channel_result.scalar_one_or_none()
            if not channel:
                logger.warning(f"Notification channel not found: {channel_id}")
                continue

            if not channel.is_enabled:
                logger.warning(f"Notification channel disabled: {channel.name}")
                continue

            channel_config = json.loads(channel.config) if isinstance(channel.config, str) else channel.config
            target_recipients = recipients or channel_config.get("recipients", [])

            for recipient in target_recipients:
                log = await self.repo.create(
                    channel_id=channel.id,
                    channel_type=channel.channel_type,
                    recipient=recipient,
                    subject=subject,
                    content=content,
                    status="pending",
                    related_alert_id=related_alert_id,
                )

                try:
                    await self._dispatch(channel.channel_type, channel_config, recipient, subject, content)
                    updated_log = await self.repo.update(
                        log.id,
                        status="sent",
                        sent_at=datetime.now(timezone.utc),
                    )
                    results.append(updated_log or log)
                except Exception as e:
                    logger.error(f"Failed to send notification to {recipient}: {e}")
                    updated_log = await self.repo.update(
                        log.id,
                        status="failed",
                        error_message=str(e)[:500],
                    )
                    results.append(updated_log or log)

        return results

    async def _dispatch(
        self,
        channel_type: str,
        config: Dict[str, Any],
        recipient: str,
        subject: Optional[str],
        content: str,
    ):
        dispatchers = {
            "email": self._send_email,
            "webhook": self._send_webhook,
            "dingtalk": self._send_dingtalk,
            "wecom": self._send_wecom,
            "lark": self._send_lark,
        }
        dispatcher = dispatchers.get(channel_type)
        if not dispatcher:
            raise ValidationException(f"Unsupported channel type: {channel_type}")
        await dispatcher(config, recipient, subject, content)

    async def _send_email(self, config: Dict, recipient: str,
                          subject: Optional[str], content: str):
        smtp_host = config.get("smtp_host", "")
        smtp_port = config.get("smtp_port", 587)
        smtp_user = config.get("smtp_user", "")
        smtp_password = config.get("smtp_password", "")
        from_addr = config.get("from_address", smtp_user)
        use_tls = config.get("use_tls", True)

        import aiosmtplib
        from email.mime.text import MIMEText

        msg = MIMEText(content, "html" if "<" in content else "plain", "utf-8")
        msg["From"] = from_addr
        msg["To"] = recipient
        msg["Subject"] = subject or "OpsNexus 通知"

        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=use_tls,
        )

    async def _send_webhook(self, config: Dict, recipient: str,
                            subject: Optional[str], content: str):
        url = config.get("url", "")
        if not url or not url.startswith(("http://", "https://")):
            raise Exception(f"Invalid webhook URL: {url}")

        headers = config.get("headers", {})
        method = config.get("method", "POST").upper()
        supported_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        if method not in supported_methods:
            raise Exception(f"Unsupported webhook HTTP method: {method}")

        payload = {
            "subject": subject,
            "content": content,
            "recipient": recipient,
            "source": "OpsNexus",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                response = await client.get(url, params=payload, headers=headers)
            else:
                response = await getattr(client, method.lower())(url, json=payload, headers=headers)

            if response.status_code >= 400:
                raise Exception(f"Webhook returned {response.status_code}: {response.text[:200]}")

    async def _send_dingtalk(self, config: Dict, recipient: str,
                             subject: Optional[str], content: str):
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            raise ValidationException("DingTalk webhook_url is required")
        secret = config.get("secret", "")
        msg_type = config.get("msg_type", "text")
        at_mobiles = config.get("at_mobiles", [])
        is_at_all = config.get("is_at_all", False)

        import time
        import hmac
        import hashlib
        import base64
        import urllib.parse

        headers = {"Content-Type": "application/json"}
        url = webhook_url

        if secret:
            timestamp = str(int(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            separator = "&" if "?" in webhook_url else "?"
            url = f"{webhook_url}{separator}timestamp={timestamp}&sign={sign}"

        text_content = f"**{subject or 'OpsNexus 通知'}**\n\n{content}" if subject else content

        if msg_type == "markdown":
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": subject or "OpsNexus 通知",
                    "text": text_content,
                },
                "at": {
                    "atMobiles": at_mobiles,
                    "isAtAll": is_at_all,
                },
            }
        else:
            payload = {
                "msgtype": "text",
                "text": {"content": text_content},
                "at": {
                    "atMobiles": at_mobiles,
                    "isAtAll": is_at_all,
                },
            }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
            result = response.json()
            if result.get("errcode") != 0:
                raise Exception(f"DingTalk error: {result.get('errmsg', 'Unknown error')}")

    async def _send_wecom(self, config: Dict, recipient: str,
                          subject: Optional[str], content: str):
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            raise ValidationException("WeCom webhook_url is required")
        msg_type = config.get("msg_type", "text")
        mentioned_list = config.get("mentioned_list", [])
        mentioned_mobile_list = config.get("mentioned_mobile_list", [])

        headers = {"Content-Type": "application/json"}
        text_content = f"**{subject or 'OpsNexus 通知'}**\n\n{content}" if subject else content

        if msg_type == "markdown":
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": text_content},
            }
        else:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": text_content,
                    "mentioned_list": mentioned_list,
                    "mentioned_mobile_list": mentioned_mobile_list,
                },
            }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(webhook_url, json=payload, headers=headers)
            result = response.json()
            if result.get("errcode") != 0:
                raise Exception(f"WeCom error: {result.get('errmsg', 'Unknown error')}")

    async def _send_lark(self, config: Dict, recipient: str,
                         subject: Optional[str], content: str):
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            raise ValidationException("Lark webhook_url is required")
        secret = config.get("secret", "")
        msg_type = config.get("msg_type", "text")

        import time
        import hmac
        import hashlib
        import base64

        headers = {"Content-Type": "application/json"}

        text_content = f"**{subject or 'OpsNexus 通知'}**\n\n{content}" if subject else content

        payload = {
            "msg_type": "interactive" if msg_type == "interactive" else "text",
        }

        if msg_type == "interactive":
            payload["card"] = {
                "header": {
                    "title": {"content": subject or "OpsNexus 通知", "tag": "plain_text"},
                },
                "elements": [
                    {"tag": "markdown", "content": content},
                ],
            }
        else:
            payload["content"] = {"text": text_content}

        if secret:
            timestamp = str(int(time.time()))
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
            sign = base64.b64encode(hmac_code).decode("utf-8")
            payload["timestamp"] = timestamp
            payload["sign"] = sign

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(webhook_url, json=payload, headers=headers)
            result = response.json()
            if result.get("code") != 0:
                raise Exception(f"Lark error: {result.get('msg', 'Unknown error')}")

    async def retry_failed(self, log_ids: List[UUID]) -> int:
        success_count = 0
        for log_id in log_ids:
            log = await self.repo.get_by_id(log_id)
            if not log or log.status not in ("failed", "retrying"):
                continue

            channel_result = await self.session.execute(
                select(NotificationChannel).where(NotificationChannel.id == log.channel_id)
            )
            channel = channel_result.scalar_one_or_none()
            if not channel or not channel.is_enabled:
                continue

            channel_config = json.loads(channel.config) if isinstance(channel.config, str) else channel.config

            try:
                await self.repo.update(log_id, status="retrying")
                await self._dispatch(
                    channel.channel_type, channel_config,
                    log.recipient, log.subject, log.content,
                )
                await self.repo.update(
                    log_id,
                    status="sent",
                    sent_at=datetime.now(timezone.utc),
                    retry_count=log.retry_count + 1,
                )
                success_count += 1
            except Exception as e:
                await self.repo.update(
                    log_id,
                    status="failed",
                    error_message=str(e)[:500],
                    retry_count=log.retry_count + 1,
                )

        return success_count

    async def list_all(self, **kwargs) -> Tuple[List[NotificationLog], int]:
        return await self.repo.list_all(**kwargs)

    async def get_stats(self) -> NotificationStatsResponse:
        stats = await self.repo.get_stats()
        return NotificationStatsResponse(**stats)


AUDIT_ACTION_MAP = {
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
    "GET": "read",
}

RESOURCE_TYPE_MAP = {
    "/api/v1/system/users": "user",
    "/api/v1/system/roles": "role",
    "/api/v1/system/configs": "system_config",
    "/api/v1/system/channels": "notification_channel",
    "/api/v1/asset/data-centers": "data_center",
    "/api/v1/asset/racks": "rack",
    "/api/v1/asset/servers": "server",
    "/api/v1/asset/bmc-credentials": "bmc_credential",
    "/api/v1/outband": "outband",
    "/api/v1/monitor/definitions": "metric_definition",
    "/api/v1/monitor/rules": "alert_rule",
    "/api/v1/monitor/events": "alert_event",
    "/api/v1/monitor/collect": "metric_collection",
    "/api/v1/audit": "audit",
    "/api/v1/autoops": "autoops",
}


def parse_resource_from_path(path: str) -> str:
    for prefix, resource_type in RESOURCE_TYPE_MAP.items():
        if path.startswith(prefix):
            return resource_type
    parts = path.strip("/").split("/")
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


SKIP_AUDIT_PATHS = {
    "/api/v1/system/auth/login",
    "/api/v1/system/auth/refresh",
    "/api/v1/system/auth/me",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
}
