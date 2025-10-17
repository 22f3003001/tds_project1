from flask import Flask, request, jsonify
import os
import json
import threading
import time
from datetime import datetime
from code_generator import CodeGenerator
from github_manager import GitHubManager
from evaluator import submit_to_evaluation

app = Flask(__name__)

# Configuration - SET THESE IN ENVIRONMENT VARIABLES
SECRET_CODE = os.getenv('SECRET_CODE', 'your-secret-here')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
LLM_API_KEY = os.getenv('LLM_API_KEY')  # Groq, OpenAI, or Anthropic
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')  # groq, openai, anthropic

# Simple in-memory storage (can be replaced with SQLite)
tasks_db = {}
processing_status = {}

def process_task_async(task_data):
    """Background task processor"""
    email = task_data['email']
    task_id = task_data['task']
    round_num = task_data['round']
    
    try:
        processing_status[task_id] = {'status': 'processing', 'step': 'initializing'}
        
        # Step 1: Generate code using LLM
        processing_status[task_id]['step'] = 'generating_code'
        generator = CodeGenerator(
            api_key=LLM_API_KEY,
            provider=LLM_PROVIDER
        )
        
        code_files = generator.generate_app(
            brief=task_data['brief'],
            checks=task_data['checks'],
            attachments=task_data.get('attachments', [])
        )
        
        # Step 2: Create/Update GitHub repo
        processing_status[task_id]['step'] = 'creating_repo'
        gh_manager = GitHubManager(
            token=GITHUB_TOKEN,
            username=GITHUB_USERNAME
        )
        
        repo_name = f"{task_id}"
        
        if round_num == 1:
            # Create new repo
            repo_url, commit_sha, pages_url = gh_manager.create_repo(
                repo_name=repo_name,
                files=code_files,
                description=f"Project: {task_id}"
            )
        else:
            # Update existing repo
            repo_url, commit_sha, pages_url = gh_manager.update_repo(
                repo_name=repo_name,
                files=code_files
            )
        
        # Step 3: Submit to evaluation API
        processing_status[task_id]['step'] = 'submitting_evaluation'
        submission_data = {
            'email': email,
            'task': task_id,
            'round': round_num,
            'nonce': task_data['nonce'],
            'repo_url': repo_url,
            'commit_sha': commit_sha,
            'pages_url': pages_url
        }
        
        success = submit_to_evaluation(
            url=task_data['evaluation_url'],
            data=submission_data
        )
        
        processing_status[task_id] = {
            'status': 'completed' if success else 'failed',
            'step': 'done',
            'repo_url': repo_url,
            'commit_sha': commit_sha,
            'pages_url': pages_url,
            'submitted': success,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store in tasks_db
        tasks_db[f"{email}_{task_id}_{round_num}"] = {
            'task_data': task_data,
            'result': processing_status[task_id]
        }
        
    except Exception as e:
        processing_status[task_id] = {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

@app.route('/api/task', methods=['POST'])
def handle_task():
    """Main endpoint to receive task requests"""
    try:
        # Parse request
        task_data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'secret', 'task', 'round', 'nonce', 
                          'brief', 'checks', 'evaluation_url']
        for field in required_fields:
            if field not in task_data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        # Verify secret
        if task_data['secret'] != SECRET_CODE:
            return jsonify({'error': 'Invalid secret'}), 403
        
        # Log the request
        print(f"[{datetime.utcnow()}] Received task: {task_data['task']} Round {task_data['round']}")
        
        # Start async processing
        thread = threading.Thread(
            target=process_task_async,
            args=(task_data,)
        )
        thread.daemon = True
        thread.start()
        
        # Return immediate 200 response
        return jsonify({
            'status': 'accepted',
            'message': 'Task received and processing started',
            'task': task_data['task'],
            'round': task_data['round']
        }), 200
        
    except Exception as e:
        print(f"Error handling task: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<task_id>', methods=['GET'])
def check_status(task_id):
    """Check processing status of a task"""
    if task_id in processing_status:
        return jsonify(processing_status[task_id]), 200
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'config': {
            'github_configured': bool(GITHUB_TOKEN and GITHUB_USERNAME),
            'llm_configured': bool(LLM_API_KEY),
            'llm_provider': LLM_PROVIDER
        }
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        'service': 'LLM Code Deployment API',
        'endpoints': {
            'task': '/api/task (POST)',
            'status': '/api/status/<task_id> (GET)',
            'health': '/api/health (GET)'
        }
    }), 200

if __name__ == '__main__':
    # Run the app
    port = int(os.getenv('PORT', 7860))  # 7860 is HuggingFace default
    app.run(host='0.0.0.0', port=port, debug=False)
