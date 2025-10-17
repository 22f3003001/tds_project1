import requests
import time
from typing import Dict

def submit_to_evaluation(url: str, data: Dict, max_retries: int = 5) -> bool:
    """
    Submit results to evaluation API with exponential backoff
    Returns: True if successful, False otherwise
    """
    headers = {
        "Content-Type": "application/json"
    }
    
    retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff
    
    for attempt, delay in enumerate(retry_delays[:max_retries], 1):
        try:
            print(f"Submitting to evaluation API (attempt {attempt}/{max_retries})...")
            print(f"URL: {url}")
            print(f"Data: {data}")
            
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✓ Evaluation submission successful!")
                print(f"Response: {response.text}")
                return True
            else:
                print(f"✗ Evaluation submission failed with status {response.status_code}")
                print(f"Response: {response.text}")
                
                # Don't retry if client error (4xx)
                if 400 <= response.status_code < 500:
                    print("Client error - not retrying")
                    return False
                
        except requests.exceptions.Timeout:
            print(f"✗ Request timeout on attempt {attempt}")
        except requests.exceptions.RequestException as e:
            print(f"✗ Request error on attempt {attempt}: {str(e)}")
        
        # Wait before retrying (except on last attempt)
        if attempt < max_retries:
            print(f"Waiting {delay} seconds before retry...")
            time.sleep(delay)
    
    print(f"✗ Failed to submit after {max_retries} attempts")
    return False

def verify_pages_accessible(pages_url: str, max_wait: int = 60) -> bool:
    """
    Verify that GitHub Pages is accessible
    Returns: True if accessible, False otherwise
    """
    print(f"Verifying GitHub Pages accessibility: {pages_url}")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(pages_url, timeout=10)
            if response.status_code == 200:
                print(f"✓ GitHub Pages is accessible")
                return True
        except:
            pass
        
        time.sleep(5)
    
    print(f"✗ GitHub Pages not accessible after {max_wait} seconds")
    return False
