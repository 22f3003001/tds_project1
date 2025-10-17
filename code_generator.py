import os
import json
import base64
from typing import List, Dict
import requests

class CodeGenerator:
    """Generates code using LLM APIs"""
    
    def __init__(self, api_key: str, provider: str = 'groq'):
        self.api_key = api_key
        self.provider = provider.lower()
        
    def generate_app(self, brief: str, checks: List[str], attachments: List[Dict]) -> Dict[str, str]:
        """
        Generate a complete web application based on brief and checks
        Returns: Dict with filenames as keys and content as values
        """
        # Prepare attachments info
        attachments_info = self._process_attachments(attachments)
        
        # Create the prompt
        prompt = self._create_prompt(brief, checks, attachments_info)
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Parse response and extract files
        files = self._parse_response(response, attachments)
        
        # Add LICENSE and README if not present
        files = self._add_required_files(files, brief, checks)
        
        return files
    
    def _process_attachments(self, attachments: List[Dict]) -> str:
        """Process attachments and return formatted info"""
        if not attachments:
            return "No attachments provided."
        
        info = "Attachments:\n"
        for att in attachments:
            name = att.get('name', 'unknown')
            url = att.get('url', '')
            
            # Extract data from data URI
            if url.startswith('data:'):
                # Parse data URI
                parts = url.split(',', 1)
                if len(parts) == 2:
                    mime_info = parts[0]
                    data = parts[1]
                    
                    # Decode if base64
                    if 'base64' in mime_info:
                        try:
                            decoded = base64.b64decode(data).decode('utf-8', errors='ignore')
                            info += f"- {name}: {decoded[:200]}...\n"
                        except:
                            info += f"- {name}: [binary data]\n"
                    else:
                        info += f"- {name}: {data[:200]}...\n"
            else:
                info += f"- {name}: {url}\n"
        
        return info
    
    def _create_prompt(self, brief: str, checks: List[str], attachments_info: str) -> str:
        """Create the LLM prompt"""
        checks_str = "\n".join([f"- {check}" for check in checks])
        
        prompt = f"""You are an expert web developer. Create a complete, functional single-page web application based on the following requirements.

BRIEF:
{brief}

CHECKS (These will be tested):
{checks_str}

{attachments_info}

REQUIREMENTS:
1. Create a single HTML file with embedded CSS and JavaScript
2. Use CDN links for any libraries (Bootstrap, marked, highlight.js, etc.)
3. Make the code clean, well-commented, and professional
4. Ensure ALL checks will pass
5. If attachments are provided as data URIs, embed them directly in the code or fetch them
6. The app should be fully functional and production-ready
7. Handle errors gracefully
8. Use modern ES6+ JavaScript

OUTPUT FORMAT:
Provide the complete HTML file content. Start with <!DOCTYPE html> and include everything in a single file.
After the HTML file, if needed, provide a README.md with:
- Project title and description
- Features
- How to use
- Code structure explanation
- Technologies used

Use this format:
=== index.html ===
[HTML content here]

=== README.md ===
[README content here]

Now generate the complete application code:"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API"""
        if self.provider == 'gemini':
            return self._call_gemini(prompt)
        elif self.provider == 'openai':
            return self._call_openai(prompt)
        elif self.provider == 'anthropic':
            return self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini model via AIPipe"""
        url = "https://aipipe.iitm.ac.in/gemini/v1/models/gemini-1.5-flash:generateContent"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"You are an expert web developer who creates clean, functional code.\n\n{prompt}"
                        }
                    ]
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text']

    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",  # Cheap and fast
            "messages": [
                {"role": "system", "content": "You are an expert web developer who creates clean, functional code."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 8000
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 8000,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        return response.json()['content'][0]['text']
    
    def _parse_response(self, response: str, attachments: List[Dict]) -> Dict[str, str]:
        """Parse LLM response and extract files"""
        files = {}
        
        # Look for file markers
        lines = response.split('\n')
        current_file = None
        current_content = []
        
        for line in lines:
            # Check for file markers
            if line.strip().startswith('=== ') and line.strip().endswith(' ==='):
                # Save previous file
                if current_file:
                    files[current_file] = '\n'.join(current_content).strip()
                
                # Start new file
                current_file = line.strip().replace('=== ', '').replace(' ===', '').strip()
                current_content = []
            elif current_file:
                current_content.append(line)
        
        # Save last file
        if current_file:
            files[current_file] = '\n'.join(current_content).strip()
        
        # If no files found, assume entire response is index.html
        if not files:
            # Try to find HTML content
            if '<!DOCTYPE html>' in response or '<html' in response:
                files['index.html'] = response.strip()
            else:
                # Wrap in basic HTML
                files['index.html'] = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated App</title>
</head>
<body>
    {response}
</body>
</html>"""
        
        # Save attachments as separate files
        for att in attachments:
            name = att.get('name', '')
            url = att.get('url', '')
            if name and url.startswith('data:'):
                files[name] = url  # Store data URI directly
        
        return files
    
    def _add_required_files(self, files: Dict[str, str], brief: str, checks: List[str]) -> Dict[str, str]:
        """Add LICENSE and README if missing"""
        
        # Add MIT LICENSE
        if 'LICENSE' not in files and 'LICENSE.md' not in files:
            files['LICENSE'] = """MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
        
        # Add README if missing
        if 'README.md' not in files:
            files['README.md'] = self._generate_readme(brief, checks, files)
        
        return files
    
    def _generate_readme(self, brief: str, checks: List[str], files: Dict[str, str]) -> str:
        """Generate a professional README"""
        checks_str = "\n".join([f"- {check}" for check in checks])
        
        return f"""# Web Application

## Description
{brief}

## Features
This application fulfills the following requirements:
{checks_str}

## Setup
1. Clone this repository
2. Open `index.html` in a web browser
3. No build process or dependencies required!

## Usage
Simply open the `index.html` file in your browser. The application is fully self-contained with all necessary CDN resources loaded automatically.

## Code Structure
- **index.html**: Main application file containing HTML, CSS, and JavaScript
- All external libraries are loaded via CDN for reliability
- Modern ES6+ JavaScript is used throughout
- Responsive design ensures compatibility across devices

## Technologies Used
- HTML5
- CSS3
- JavaScript (ES6+)
- External libraries as specified in requirements

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Generated
This application was automatically generated based on project requirements."""
        
        return
