"""
Local testing script - Test your setup before deploying
Run with: python test_local.py
"""

import os
import json
import base64

# Test configuration
print("=" * 60)
print("TESTING CONFIGURATION")
print("=" * 60)

# Check environment variables
required_vars = {
    'SECRET_CODE': 'Your secret from the form',
    'GITHUB_TOKEN': 'GitHub Personal Access Token',
    'GITHUB_USERNAME': 'Your GitHub username',
    'LLM_API_KEY': 'LLM API Key (Groq/OpenAI/Anthropic)',
    'LLM_PROVIDER': 'groq, openai, or anthropic'
}

all_set = True
for var, description in required_vars.items():
    value = os.getenv(var)
    if value:
        masked = value[:4] + '***' if len(value) > 4 else '***'
        print(f"✓ {var}: {masked} ({description})")
    else:
        print(f"✗ {var}: NOT SET ({description})")
        all_set = False

if not all_set:
    print("\n⚠️  Some environment variables are missing!")
    print("Set them using:")
    print("  export SECRET_CODE='your-secret'")
    print("  export GITHUB_TOKEN='ghp_...'")
    print("  export GITHUB_USERNAME='yourusername'")
    print("  export LLM_API_KEY='your-api-key'")
    print("  export LLM_PROVIDER='groq'")
    exit(1)

print("\n" + "=" * 60)
print("TESTING GITHUB CONNECTION")
print("=" * 60)

try:
    from github_manager import GitHubManager
    
    gh = GitHubManager(
        token=os.getenv('GITHUB_TOKEN'),
        username=os.getenv('GITHUB_USERNAME')
    )
    
    user = gh.user
    print(f"✓ Connected to GitHub as: {user.login}")
    print(f"✓ Account type: {user.type}")
    print(f"✓ Public repos: {user.public_repos}")
    
except Exception as e:
    print(f"✗ GitHub connection failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("TESTING LLM CONNECTION")
print("=" * 60)

try:
    from code_generator import CodeGenerator
    
    generator = CodeGenerator(
        api_key=os.getenv('LLM_API_KEY'),
        provider=os.getenv('LLM_PROVIDER', 'groq')
    )
    
    # Simple test prompt
    test_prompt = "Create a simple HTML page that says 'Hello World' in an h1 tag."
    
    print(f"Testing {generator.provider.upper()} API...")
    response = generator._call_llm(test_prompt)
    
    if 'hello' in response.lower():
        print(f"✓ {generator.provider.upper()} API is working!")
        print(f"✓ Response length: {len(response)} characters")
    else:
        print(f"⚠️  Got response but it seems unusual")
        print(f"Response preview: {response[:200]}...")
    
except Exception as e:
    print(f"✗ LLM connection failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("CREATING TEST SAMPLE")
print("=" * 60)

# Create a sample CSV for testing
test_csv_data = """product,sales,region
Widget A,1500.50,North
Widget B,2300.75,South
Widget C,1800.25,East"""

test_csv_b64 = base64.b64encode(test_csv_data.encode()).decode()

# Sample task request
sample_task = {
    "email": "test@example.com",
    "secret": os.getenv('SECRET_CODE'),
    "task": "sum-of-sales-test123",
    "round": 1,
    "nonce": "test-nonce-12345",
    "brief": "Create a single-page site that displays 'Test Application' in an h1 tag with id='title'.",
    "checks": [
        "Page has an h1 tag with id='title'",
        "h1 contains text 'Test Application'"
    ],
    "evaluation_url": "https://httpbin.org/post",  # Test endpoint
    "attachments": []
}

print("Sample task created:")
print(json.dumps(sample_task, indent=2))

print("\n" + "=" * 60)
print("TESTING FULL FLOW")
print("=" * 60)

try:
    # Generate code
    print("1. Generating code...")
    files = generator.generate_app(
        brief=sample_task['brief'],
        checks=sample_task['checks'],
        attachments=sample_task['attachments']
    )
    print(f"✓ Generated {len(files)} files: {list(files.keys())}")
    
    # Create repo
    print("\n2. Creating GitHub repo...")
    repo_url, commit_sha, pages_url = gh.create_repo(
        repo_name=sample_task['task'],
        files=files,
        description="Test repo - can be deleted"
    )
    print(f"✓ Repo created: {repo_url}")
    print(f"✓ Commit: {commit_sha}")
    print(f"✓ Pages: {pages_url}")
    
    # Submit to evaluation
    print("\n3. Submitting to evaluation...")
    from evaluator import submit_to_evaluation
    
    result = submit_to_evaluation(
        url=sample_task['evaluation_url'],
        data={
            'email': sample_task['email'],
            'task': sample_task['task'],
            'round': sample_task['round'],
            'nonce': sample_task['nonce'],
            'repo_url': repo_url,
            'commit_sha': commit_sha,
            'pages_url': pages_url
        }
    )
    
    if result:
        print("✓ Evaluation submission successful!")
    else:
        print("⚠️  Evaluation submission failed (but this is expected for test endpoint)")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print(f"\nYour test repo: {repo_url}")
    print(f"GitHub Pages (may take 1-2 min): {pages_url}")
    print("\nYou can now deploy to Hugging Face!")
    print(f"\n⚠️  Remember to delete the test repo: {repo_url}")
    
except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
