# mtg-listings-scraper
A simple system to scrape listed magic cards and historical sales prices from TCGPlayer, then generate an email report of listings that compare favorably with the historical prices.

# Setup 
Three files are required to run this process:
1. `tcgplayer_scraper.py`: Performs all the core functionality of scraping, analysis, and emailing results. Run this script to initiate the process.
2. `creds.py`: You must create this file. It contains your gmail credentials and other information necessary for sending an email. See `creds_example.py` for a template. 
4. `searchUrls.txt`: A list of urls the scraper should check on TCGplayer for specific card listings, e.g. https://www.tcgplayer.com/product/8989/magic-unlimited-edition-black-lotus. Use line breaks to separate urls. 

# Reference
This is heavily modified from but based on the scripting provided by @davidteather here: https://github.com/davidteather/TCGPlayer-Scraper
