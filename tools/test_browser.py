from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://www.g2.com/categories/supply-chain-management')
    print(page.title())
    print(page.inner_text('body')[:2000])
    browser.close()