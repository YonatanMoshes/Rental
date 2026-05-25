"""Enumeration types for the application."""

from enum import StrEnum


class VehicleStatus(StrEnum):
    """Possible states for a vehicle in the fleet.
    
    - AVAILABLE: Ready to rent
    - RENTED: Currently rented by a customer
    - MAINTENANCE: Under maintenance, unavailable for rent
    """
    AVAILABLE = "available"
    RENTED = "rented"
    MAINTENANCE = "maintenance"
