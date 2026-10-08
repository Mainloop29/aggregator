class DomainError(Exception):
    """Базовый класс для ошибок бизнес-логики."""


class EventNotFound(DomainError):
    """Событие не найдено в нашей БД."""


class EventNotPublished(DomainError):
    """Событие не в статусе published."""


class EventInPast(DomainError):
    """Событие уже прошло."""


class RegistrationClosed(DomainError):
    """Дедлайн регистрации истёк."""


class TicketNotFound(DomainError):
    """Тикет не найден."""


class SeatNotAvailable(DomainError):
    """Место уже занято."""


class InvalidSeat(DomainError):
    """Место не соответствует seats_pattern."""


class ProviderUnavailable(DomainError):
    """Events Provider API недоступен или вернул ошибку."""
