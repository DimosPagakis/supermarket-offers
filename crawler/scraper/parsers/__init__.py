"""Per-brand HTML-to-OfferItem parsers.

Kept dependency-free of Scrapy so they can be exercised against saved
fixtures in plain pytest. Spiders are thin shells that call into here.
"""
