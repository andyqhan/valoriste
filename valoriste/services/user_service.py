"""
User service for managing user data and preferences
"""
from typing import Optional, Dict, List
from ..models.user import User, UserSizes, UserPreferences, Gender

class UserService:
    """Service for managing users"""
    
    def __init__(self, db_client=None):
        self.db = db_client
        # Temporary in-memory store until DB is set up
        self._users = self._init_demo_users()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    def _init_demo_users(self) -> Dict[str, User]:
        """Initialize demo users - temporary until DB is set up"""
        return {
            "rose": User(
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
            ),
            "thai": User(
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
            ),
            "andy": User(
                id="andy",
                name="Andy",
                gender=Gender.MEN,
                sizes=UserSizes(
                    tops=['S', 'M'],
                    bottoms_waist=['28', '29'],
                    bottoms_letter=['S', 'M'],
                    outerwear=['S', 'M']
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
        } 