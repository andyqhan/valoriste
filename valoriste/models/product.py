"""
Product model for Valoriste
"""
from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal

@dataclass
class Product:
    """Product class for storing item information"""
    title: str
    brand: str
    price: Decimal
    url: str
    size: Optional[str] = None
    theo_price: Decimal = field(default_factory=lambda: Decimal('0.0'))
    potential_profit: Decimal = field(default_factory=lambda: Decimal('0.0'))
    roi: float = 0.0
    condition: Optional[str] = None
    shipping_cost: Decimal = field(default_factory=lambda: Decimal('0.0'))
    
    def __post_init__(self):
        """Validate and normalize values"""
        # Convert price strings to Decimal
        if isinstance(self.price, (str, float)):
            self.price = Decimal(str(self.price))
        if isinstance(self.theo_price, (str, float)):
            self.theo_price = Decimal(str(self.theo_price))
        if isinstance(self.potential_profit, (str, float)):
            self.potential_profit = Decimal(str(self.potential_profit))
        if isinstance(self.shipping_cost, (str, float)):
            self.shipping_cost = Decimal(str(self.shipping_cost))
            
        # Ensure non-negative values
        self.price = max(self.price, Decimal('0.0'))
        self.theo_price = max(self.theo_price, Decimal('0.0'))
        self.potential_profit = max(self.potential_profit, Decimal('0.0'))
        self.shipping_cost = max(self.shipping_cost, Decimal('0.0'))
        self.roi = max(self.roi, 0.0)
        
        # Normalize size
        if self.size:
            self.size = str(self.size).upper()

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost including shipping"""
        return self.price + self.shipping_cost

    def calculate_profit(self, ebay_fee_percentage: float = 12.9) -> None:
        """Calculate potential profit and ROI"""
        if self.theo_price > 0:
            ebay_fees = self.theo_price * Decimal(str(ebay_fee_percentage / 100))
            self.potential_profit = self.theo_price - self.total_cost - ebay_fees
            if self.total_cost > 0:
                self.roi = float((self.potential_profit / self.total_cost) * 100) 