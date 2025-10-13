"""
Scraper Service - Handles web scraping for broadband comparison data.
Wraps the jmi_scrapper module for clean service-oriented architecture.
"""

import sys
import os
import asyncio
from typing import Dict, Optional
from loguru import logger

try:
    from jmi_broadband_agent.lib.jmi_scrapper import BroadbandScraper
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False
    logger.warning("⚠️ Broadband scraper module not available")


class ScraperService:
    """
    Service for scraping broadband comparison data.
    Provides a clean interface for data extraction operations.
    """
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize the scraper service.
        
        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.scraper = None
        
        if SCRAPER_AVAILABLE:
            try:
                self.scraper = BroadbandScraper(headless=headless, timeout=timeout)
                logger.info("✅ Scraper service initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize scraper: {e}")
                self.scraper = None
        else:
            logger.warning("⚠️ Scraper not available - service will return mock data")
    
    async def scrape_url_async(self, url: str, wait_time: int = 5) -> Dict:
        """
        Asynchronously scrape a broadband comparison URL.
        
        Args:
            url: The URL to scrape
            wait_time: Wait time in seconds for dynamic content
            
        Returns:
            Structured dictionary with scraped data
        """
        if not self.scraper:
            return self._get_mock_response(url, "Scraper not available")
        
        try:
            logger.info(f"🔍 Scraping URL: {url}")
            result = await self.scraper.scrape_url_async(url, wait_time)
            
            if result.get('error'):
                logger.error(f"❌ Scraping error: {result['error']}")
            else:
                logger.info(f"✅ Successfully scraped {result.get('total_deals', 0)} deals")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Scraping exception: {e}")
            return self._get_mock_response(url, str(e))
    
    def scrape_url_sync(self, url: str, wait_time: int = 5) -> Dict:
        """
        Synchronously scrape a broadband comparison URL.
        
        Args:
            url: The URL to scrape
            wait_time: Wait time in seconds for dynamic content
            
        Returns:
            Structured dictionary with scraped data
        """
        if not self.scraper:
            return self._get_mock_response(url, "Scraper not available")
        
        try:
            logger.info(f"🔍 Scraping URL (sync): {url}")
            
            # Use the fast scraping method
            result = self.scraper.scrape_url_fast(url)
            
            if result.get('error'):
                logger.error(f"❌ Scraping error: {result['error']}")
            else:
                logger.info(f"✅ Successfully scraped {result.get('total_deals', 0)} deals")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Scraping exception: {e}")
            return self._get_mock_response(url, str(e))
    
    async def scrape_url_fast_async(self, url: str) -> Dict:
        """
        Fast async scraping method with multiple fallback strategies.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Structured dictionary with scraped data
        """
        if not self.scraper:
            return self._get_mock_response(url, "Scraper not available")
        
        try:
            logger.info(f"⚡ Fast scraping URL: {url}")
            result = await self.scraper.scrape_url_fast_async(url)
            
            if result.get('error'):
                logger.error(f"❌ Fast scraping error: {result['error']}")
            else:
                logger.info(f"✅ Fast scrape completed: {result.get('total_deals', 0)} deals")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Fast scraping exception: {e}")
            return self._get_mock_response(url, str(e))
    
    def _get_mock_response(self, url: str, error_message: str) -> Dict:
        """
        Generate a mock response when scraping fails.
        
        Args:
            url: The URL that was attempted
            error_message: Error description
            
        Returns:
            Mock response dictionary
        """
        return {
            'url': url,
            'error': error_message,
            'total_deals': 0,
            'deals': [],
            'metadata': {
                'location': 'Unknown',
                'page_title': 'Error'
            },
            'filters_applied': {},
            'scrape_timestamp': None,
            'note': 'This is a mock response due to scraper unavailability'
        }
    
    def extract_deal_summary(self, scraped_data: Dict) -> Dict:
        """
        Extract a summary from scraped data.
        
        Args:
            scraped_data: Full scraped data dictionary
            
        Returns:
            Summary dictionary with key metrics
        """
        if not scraped_data or scraped_data.get('error'):
            return {
                'total_deals': 0,
                'error': scraped_data.get('error', 'No data'),
                'has_deals': False
            }
        
        deals = scraped_data.get('deals', [])
        
        if not deals:
            return {
                'total_deals': 0,
                'has_deals': False,
                'location': scraped_data.get('metadata', {}).get('location', 'Unknown')
            }
        
        # Extract key metrics
        providers = set()
        speeds = []
        prices = []
        
        for deal in deals:
            if deal.get('provider', {}).get('name'):
                providers.add(deal['provider']['name'])
            
            if deal.get('speed', {}).get('numeric'):
                try:
                    speeds.append(float(deal['speed']['numeric']))
                except (ValueError, TypeError):
                    pass
            
            if deal.get('pricing', {}).get('monthly_cost'):
                try:
                    price_str = deal['pricing']['monthly_cost']
                    # Extract numeric value from string like "£25.00"
                    import re
                    price_match = re.search(r'[\d.]+', price_str)
                    if price_match:
                        prices.append(float(price_match.group()))
                except (ValueError, TypeError):
                    pass
        
        summary = {
            'total_deals': len(deals),
            'has_deals': True,
            'location': scraped_data.get('metadata', {}).get('location', 'Unknown'),
            'unique_providers': len(providers),
            'providers_list': sorted(list(providers)),
        }
        
        if speeds:
            summary['speed_range'] = {
                'min': min(speeds),
                'max': max(speeds),
                'avg': sum(speeds) / len(speeds)
            }
        
        if prices:
            summary['price_range'] = {
                'min': min(prices),
                'max': max(prices),
                'avg': sum(prices) / len(prices)
            }
        
        return summary
    
    def get_cheapest_deal(self, scraped_data: Dict) -> Optional[Dict]:
        """
        Find the cheapest deal from scraped data.
        
        Args:
            scraped_data: Full scraped data dictionary
            
        Returns:
            Cheapest deal dictionary or None
        """
        deals = scraped_data.get('deals', [])
        if not deals:
            return None
        
        cheapest = None
        cheapest_price = float('inf')
        
        for deal in deals:
            price_str = deal.get('pricing', {}).get('monthly_cost', '')
            try:
                import re
                price_match = re.search(r'[\d.]+', price_str)
                if price_match:
                    price = float(price_match.group())
                    if price < cheapest_price:
                        cheapest_price = price
                        cheapest = deal
            except (ValueError, TypeError):
                continue
        
        return cheapest
    
    def get_fastest_deal(self, scraped_data: Dict) -> Optional[Dict]:
        """
        Find the fastest deal from scraped data.
        
        Args:
            scraped_data: Full scraped data dictionary
            
        Returns:
            Fastest deal dictionary or None
        """
        deals = scraped_data.get('deals', [])
        if not deals:
            return None
        
        fastest = None
        fastest_speed = 0.0
        
        for deal in deals:
            speed_str = deal.get('speed', {}).get('numeric', '')
            try:
                speed = float(speed_str)
                if speed > fastest_speed:
                    fastest_speed = speed
                    fastest = deal
            except (ValueError, TypeError):
                continue
        
        return fastest


# Global instance for easy access
_scraper_service = None


def get_scraper_service(headless: bool = True, timeout: int = 30000) -> ScraperService:
    """
    Get or create the global scraper service instance.
    
    Args:
        headless: Run browser in headless mode
        timeout: Page load timeout in milliseconds
        
    Returns:
        ScraperService instance
    """
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = ScraperService(headless=headless, timeout=timeout)
    return _scraper_service

