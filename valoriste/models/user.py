"""
User model for Valoriste
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class Gender(Enum):
    """User gender enum"""
    MEN = "men"
    WOMEN = "women"

@dataclass
class UserSizes:
    """User size preferences for different clothing types"""
    tops: List[str]
    bottoms_waist: List[str]
    bottoms_letter: List[str]
    outerwear: List[str]

    def __post_init__(self):
        """Validate and normalize sizes"""
        self.tops = [str(size).upper() for size in self.tops]
        self.bottoms_waist = [str(size) for size in self.bottoms_waist]
        self.bottoms_letter = [str(size).upper() for size in self.bottoms_letter]
        self.outerwear = [str(size).upper() for size in self.outerwear]

@dataclass
class UserPreferences:
    """User shopping preferences"""
    brands: List[str]
    min_roi: float
    max_price: float
    excluded_keywords: List[str] = field(default_factory=lambda: [
        'fake', 'replica', 'inspired', 'wholesale', 'lot', 'bulk'
    ])

    def __post_init__(self):
        """Validate and normalize preferences"""
        self.brands = [brand.strip() for brand in self.brands]
        self.excluded_keywords = [kw.lower() for kw in self.excluded_keywords]
        if self.min_roi < 0:
            self.min_roi = 0.0
        if self.max_price <= 0:
            self.max_price = float('inf')

@dataclass
class User:
    """Main user class"""
    id: str
    name: str
    gender: Gender
    sizes: UserSizes
    preferences: UserPreferences

    def __post_init__(self):
        """Validate user data"""
        if not isinstance(self.gender, Gender):
            self.gender = Gender(self.gender)

    @classmethod
    def create_rose(cls) -> 'User':
        """Create Rose's profile"""
        return cls(
            id="rose",
            name="Rose",
            gender=Gender.WOMEN,
            sizes=UserSizes(
                tops=['S', 'M'],
                bottoms_waist=['26', '27', '28'],
                bottoms_letter=['S', 'M'],
                outerwear=['S', 'M']
            ),
            preferences=UserPreferences(
                brands=[
                    'Stylenanda', 'ADER Error', '87MM', "Charm's",
                    'Musinsa Standard', 'Meshki', 'Revolve',
                    'House of CB', 'Oh Polly', 'Bardot', 'Cult Gaia',
                    'Matin Kim', 'Low Classic', 'Recto', 'TheOpen Product'
                ],
                min_roi=30.0,
                max_price=300.0,
                excluded_keywords=[
                    'men', 'mens', 'male', 'boys',
                    'fake', 'replica', 'inspired',
                    'wholesale', 'lot', 'bulk'
                ]
            )
        )

    @classmethod
    def create_thai(cls) -> 'User':
        """Create Thai's profile"""
        return cls(
            id="thai",
            name="Thai",
            gender=Gender.MEN,
            sizes=UserSizes(
                tops=['M', 'L'],
                bottoms_waist=['33', '34'],
                bottoms_letter=['M', 'L'],
                outerwear=['M', 'L']
            ),
            preferences=UserPreferences(
                brands=[
                    'Lululemon', 'Norse Projects', 'APC', 'Theory'
                ],
                min_roi=30.0,
                max_price=300.0,
                excluded_keywords=[
                    'women', 'womens', 'female', 'girls',
                    'fake', 'replica', 'inspired',
                    'wholesale', 'lot', 'bulk'
                ]
            )
        )

@dataclass
class SizePreference:
    """User's size preferences"""
    tops: List[str]  # e.g., ["L", "XL"]
    bottoms_waist: List[str]  # e.g., ["33", "34"]
    bottoms_letter: List[str]  # e.g., ["M", "L"]
    outerwear: List[str]  # e.g., ["L", "XL"]
    
    def matches_size(self, item_title: str, item_size: str) -> bool:
        """Check if an item's size matches user preferences"""
        item_title_lower = item_title.lower()
        item_size_lower = item_size.lower()
        
        # Check if it's a top
        if any(word in item_title_lower for word in ['shirt', 'tee', 'polo', 'sweater']):
            return item_size_lower in [s.lower() for s in self.tops]
            
        # Check if it's outerwear
        if any(word in item_title_lower for word in ['jacket', 'coat', 'hoodie']):
            return item_size_lower in [s.lower() for s in self.outerwear]
            
        # Check if it's bottoms
        if any(word in item_title_lower for word in ['pants', 'jeans', 'shorts', 'trousers']):
            # Check waist sizes
            if item_size_lower.replace('w', '').strip() in [s.lower() for s in self.bottoms_waist]:
                return True
            # Check letter sizes
            return item_size_lower in [s.lower() for s in self.bottoms_letter]
            
        return False

@dataclass
class UserPreferences:
    """User's shopping preferences"""
    brands: List[str]
    max_price: float
    min_roi: float
    excluded_keywords: List[str] = None  # e.g., ["women", "kids", "fake"]
    
    def __post_init__(self):
        if self.excluded_keywords is None:
            self.excluded_keywords = ["women", "kids", "fake", "replica"]
        self.brand_set = {b.lower() for b in self.brands}
    
    def matches_preferences(self, item_title: str, price: float) -> bool:
        """Check if an item matches user preferences"""
        title_lower = item_title.lower()
        
        # Check price
        if price > self.max_price:
            return False
            
        # Check excluded keywords
        if any(word in title_lower for word in self.excluded_keywords):
            return False
            
        # Check if it's from preferred brands
        return any(brand.lower() in title_lower for brand in self.brands) 