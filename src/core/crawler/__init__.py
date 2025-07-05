"""
Crawler system per architettura ibrida
Link discovery + content extraction con trafilatura
"""

from .link_discoverer import LinkDiscoverer
from .content_extractor import ContentExtractor
from .trafilatura_crawler import TrafilaturaCrawler
from .crawl_scheduler import CrawlScheduler

__all__ = [
    'LinkDiscoverer',
    'ContentExtractor', 
    'TrafilaturaCrawler',
    'CrawlScheduler'
]