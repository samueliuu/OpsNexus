import asyncio
import json
import uuid
from typing import Any, Callable, Dict, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EventBus:

    def __init__(self):
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self._lock = asyncio.Lock()

    async def connect(self):
        async with self._lock:
            if self.connection is None or self.connection.is_closed:
                self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
                self.channel = await self.connection.channel()
                self.exchange = await self.channel.declare_exchange(
                    "opsnexus.events", ExchangeType.TOPIC, durable=True
                )
                logger.info("Connected to RabbitMQ")

    async def disconnect(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")

    async def publish(
        self,
        routing_key: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ):
        try:
            if self.connection is None or self.connection.is_closed:
                await self.connect()

            if self.exchange is None:
                # Recreate exchange if connection was reestablished
                self.exchange = await self.channel.declare_exchange(
                    "opsnexus.events", ExchangeType.TOPIC, durable=True
                )
                logger.info("Recreated event exchange after reconnection")

            if correlation_id is None:
                correlation_id = str(uuid.uuid4())

            message = Message(
                body=json.dumps(payload).encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                correlation_id=correlation_id,
            )

            await self.exchange.publish(message, routing_key=routing_key)
            logger.debug(f"Published event to {routing_key}", correlation_id=correlation_id)
        except Exception as e:
            logger.error(f"Failed to publish event to {routing_key}: {e}", correlation_id=correlation_id)

    async def subscribe(
        self,
        queue_name: str,
        routing_keys: list[str],
        handler: Callable[[Dict[str, Any], str], Any],
    ):
        await self.connect()

        queue = await self.channel.declare_queue(queue_name, durable=True)

        for routing_key in routing_keys:
            await queue.bind(self.exchange, routing_key)

        async def message_handler(message: aio_pika.IncomingMessage):
            try:
                payload = json.loads(message.body.decode())
                correlation_id = message.correlation_id or str(uuid.uuid4())
                await handler(payload, correlation_id)
                await message.ack()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in message: {e}")
                await message.reject(requeue=False)
            except Exception as e:
                logger.error(f"Error handling message: {e}", correlation_id=message.correlation_id)
                await message.nack(requeue=True)

        await queue.consume(message_handler)
        logger.info(f"Subscribed to queue: {queue_name}")


# Global event bus instance
event_bus = EventBus()


# Event types
class EventTypes:
    """Event type constants."""

    # Server events
    SERVER_CREATED = "server.created"
    SERVER_UPDATED = "server.updated"
    SERVER_DELETED = "server.deleted"
    SERVER_STATUS_CHANGED = "server.status.changed"

    # BMC events
    BMC_CONNECTED = "bmc.connected"
    BMC_DISCONNECTED = "bmc.disconnected"
    BMC_ERROR = "bmc.error"

    # Alert events
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_APPROVED = "task.approved"
    TASK_CANCELLED = "task.cancelled"

    # Audit events
    AUDIT_LOG_CREATED = "audit_log.created"


async def publish_event(event_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None):
    """Publish an event to the event bus."""
    await event_bus.publish(
        routing_key=event_type,
        payload={"type": event_type, "data": payload},
        correlation_id=correlation_id,
    )
