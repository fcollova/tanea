"""
Crawler system per architettura ibrida
Link discovery + content extraction con trafilatura
"""

from .trafilatura_link_discoverer import TrafilaturaLinkDiscoverer
from .content_extractor import ContentExtractor
from .trafilatura_crawler import TrafilaturaCrawler
from .crawl_scheduler import CrawlScheduler

# Backward compatibility
LinkDiscoverer = TrafilaturaLinkDiscoverer

__all__ = [
    'TrafilaturaLinkDiscoverer',
    'LinkDiscoverer',  # Backward compatibility
    'ContentExtractor', 
    'TrafilaturaCrawler',
    'CrawlScheduler'
]