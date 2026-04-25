from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            import uuid
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(str(value))
        return value


class INET(TypeDecorator):
    impl = String(45)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import INET as PG_INET
            return dialect.type_descriptor(PG_INET())
        return dialect.type_descriptor(String(45))
