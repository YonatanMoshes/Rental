from enum import StrEnum


class VehicleStatus(StrEnum):
    AVAILABLE = "available"
    RENTED = "rented"
    MAINTENANCE = "maintenance"
