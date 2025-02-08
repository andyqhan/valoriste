"""
Notification service for Valoriste
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict
from ..models.user import User
from ..models.product import Product
from ..config import Config

class NotificationService:
    """Service for sending notifications about deals"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
    
    def notify(self, message: str, subject: str = "Valoriste Deal Alert") -> bool:
        """
        Send a notification
        
        Args:
            message: The message content
            subject: The email subject
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not all([
            self.config.SMTP_SERVER,
            self.config.SMTP_PORT,
            self.config.SMTP_USERNAME,
            self.config.SMTP_PASSWORD,
            self.config.NOTIFICATION_EMAIL
        ]):
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.SMTP_USERNAME
            msg['To'] = self.config.NOTIFICATION_EMAIL
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.config.SMTP_USERNAME, self.config.SMTP_PASSWORD)
                server.send_message(msg)
                
            return True
            
        except Exception as e:
            print(f"Failed to send notification: {str(e)}")
            return False
    
    def notify_deal(self, item: Dict, analysis: 'PriceAnalysis') -> bool:
        """
        Send a notification about a specific deal
        
        Args:
            item: Item dictionary from eBay API
            analysis: PriceAnalysis object for the item
            
        Returns:
            bool: True if notification was sent successfully
        """
        title = item.get('title', 'Unknown Item')
        current_price = float(item.get('sellingStatus', {})
                            .get('currentPrice', {})
                            .get('value', 0))
        
        message = (
            f"Deal Alert: {title}\n\n"
            f"Current Price: ${current_price:.2f}\n"
            f"Median Price: ${analysis.median_price:.2f}\n"
            f"Potential Savings: ${(analysis.median_price - current_price):.2f}\n\n"
            f"Confidence: {analysis.confidence:.1%}\n"
            f"Based on {analysis.sample_size} similar items\n\n"
            f"Link: {item.get('viewItemURL', 'N/A')}"
        )
        
        return self.notify(message, subject=f"Deal Alert: Save ${(analysis.median_price - current_price):.2f}")

    def send_daily_update(self, user: User, products: List[Product]):
        """Print daily update to console"""
        if not products:
            print(f"\nNo opportunities found for {user.name}")
            return
            
        print("\n" + "="*80)
        print(f"DAILY RESALE OPPORTUNITIES FOR {user.name.upper()}")
        print("="*80)
        
        # Group products by brand
        by_brand = {}
        for p in products:
            if p.brand not in by_brand:
                by_brand[p.brand] = []
            by_brand[p.brand].append(p)
        
        # Print products by brand
        for brand, brand_products in by_brand.items():
            print(f"\n{brand.upper()} ({len(brand_products)} items)")
            print("-"*80)
            print(f"{'ITEM':<40} {'SIZE':<6} {'PRICE':>8} {'THEO':>8} {'PROFIT':>8} {'ROI':>6}")
            print("-"*80)
            
            for p in sorted(brand_products, key=lambda x: x.roi, reverse=True):
                print(
                    f"{p.title[:37]+'...':<40} "
                    f"{p.size:<6} "
                    f"${p.price:>7.2f} "
                    f"${p.theo_price:>7.2f} "
                    f"${p.potential_profit:>7.2f} "
                    f"{p.roi:>5.1f}%"
                )
                print(f"URL: {p.url}")
                print("-"*80)
        
        # Print summary
        total_potential_profit = sum(p.potential_profit for p in products if p.potential_profit)
        avg_roi = sum(p.roi for p in products if p.roi) / len(products)
        print(f"\nSUMMARY")
        print(f"Total items found: {len(products)}")
        print(f"Total potential profit: ${total_potential_profit:.2f}")
        print(f"Average ROI: {avg_roi:.1f}%")
        print("="*80 + "\n") 