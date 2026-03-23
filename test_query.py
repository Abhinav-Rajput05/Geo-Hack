from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:3000', timeout=60000)
    page.wait_for_load_state('networkidle', timeout=60000)
    page.click('text=Query')
    page.wait_for_url('**/query')

    # Wait for the input to be visible
    page.wait_for_selector('input[placeholder*="Ask a question"]')

    # Type a question
    page.fill('input[placeholder*="Ask a question"]', 'What is the current geopolitical situation in Ukraine?')

    # Click the Ask button
    page.click('button:has-text("Ask")')

    # Wait for the result to appear or error
    page.wait_for_selector('.result-card', timeout=10000)

    # Check if result is present
    result_element = page.locator('.result-card')
    if result_element.count() > 0:
        # Check the answer text
        answer = page.locator('.result-answer').text_content()
        print(f"Answer: {answer}")

        # Check confidence
        confidence = page.locator('.confidence-badge').text_content()
        print(f"Confidence: {confidence}")

        # Check if error message
        if "Unable to fetch" in answer:
            print("Error detected: Backend not available")
        else:
            print("Query successful")

        # Check reasoning chain
        reasoning_steps = page.locator('.reasoning-step').count()
        print(f"Reasoning steps: {reasoning_steps}")

        # Check supporting facts
        facts = page.locator('.fact-item').count()
        print(f"Supporting facts: {facts}")

        # Verify completeness: if error, should have 0 confidence, 0 steps, 0 facts
        if "Unable to fetch" in answer and "0%" in confidence and reasoning_steps == 0 and facts == 0:
            print("Verification: Correct error handling - completeness and correctness verified")
        else:
            print("Verification: Unexpected response")

    else:
        print("No result card found")

    browser.close()