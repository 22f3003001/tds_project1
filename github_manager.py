from github import Github, GithubException
import time
import base64
from typing import Dict, Tuple

class GitHubManager:
    """Manages GitHub repository creation and updates"""
    
    def __init__(self, token: str, username: str):
        self.github = Github(token)
        self.user = self.github.get_user()
        self.username = username
        
    def create_repo(self, repo_name: str, files: Dict[str, str], 
                    description: str = "") -> Tuple[str, str, str]:
        """
        Create a new GitHub repository with files
        Returns: (repo_url, commit_sha, pages_url)
        """
        try:
            # Create repository
            repo = self.user.create_repo(
                name=repo_name,
                description=description,
                private=False,
                auto_init=False
            )
            
            print(f"Created repo: {repo.html_url}")
            
            # Wait a moment for repo to be ready
            time.sleep(2)
            
            # Create initial commit with all files
            commit_sha = self._create_initial_commit(repo, files)
            
            # Enable GitHub Pages
            pages_url = self._enable_pages(repo)
            
            # Wait for pages to deploy
            time.sleep(5)
            
            return repo.html_url, commit_sha, pages_url
            
        except GithubException as e:
            # If repo exists, update it instead
            if e.status == 422:
                print(f"Repo {repo_name} exists, updating instead...")
                return self.update_repo(repo_name, files)
            raise
    
    def update_repo(self, repo_name: str, files: Dict[str, str]) -> Tuple[str, str, str]:
        """
        Update an existing repository with new files
        Returns: (repo_url, commit_sha, pages_url)
        """
        try:
            repo = self.user.get_repo(repo_name)
            
            # Update each file
            for filename, content in files.items():
                self._update_or_create_file(repo, filename, content)
            
            # Get latest commit
            commits = repo.get_commits()
            latest_commit = commits[0].sha
            
            # Get pages URL
            pages_url = f"https://{self.username}.github.io/{repo_name}/"
            
            # Ensure pages is enabled
            try:
                self._enable_pages(repo)
            except:
                pass  # Pages might already be enabled
            
            return repo.html_url, latest_commit, pages_url
            
        except GithubException as e:
            print(f"Error updating repo: {e}")
            raise
    
    def _create_initial_commit(self, repo, files: Dict[str, str]) -> str:
        """Create initial commit with multiple files"""
        # Prepare all files for commit
        elements = []
        
        for filename, content in files.items():
            # Handle data URIs for attachments
            if content.startswith('data:'):
                # For data URIs, create a reference file instead
                content = f"# {filename}\n\nThis file was provided as an attachment.\nData URI: {content[:100]}..."
                filename = f"attachments/{filename}.txt"
            
            # Create blob
            blob = repo.create_git_blob(content, "utf-8")
            elements.append(
                {
                    "path": filename,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob.sha
                }
            )
        
        # Create tree
        tree = repo.create_git_tree(elements)
        
        # Create commit
        commit = repo.create_git_commit(
            message="Initial commit - Auto-generated application",
            tree=tree,
            parents=[]
        )
        
        # Update main/master branch reference
        try:
            ref = repo.get_git_ref("heads/main")
            ref.edit(commit.sha)
        except:
            # Create main branch if doesn't exist
            repo.create_git_ref("refs/heads/main", commit.sha)
        
        return commit.sha
    
    def _update_or_create_file(self, repo, filename: str, content: str):
        """Update a file if it exists, create if it doesn't"""
        try:
            # Handle data URIs
            if content.startswith('data:'):
                content = f"# {filename}\n\nThis file was provided as an attachment.\nData URI: {content[:100]}..."
                filename = f"attachments/{filename}.txt"
            
            # Try to get existing file
            try:
                file_contents = repo.get_contents(filename)
                # Update existing file
                repo.update_file(
                    path=filename,
                    message=f"Update {filename}",
                    content=content,
                    sha=file_contents.sha,
                    branch="main"
                )
                print(f"Updated: {filename}")
            except GithubException as e:
                if e.status == 404:
                    # File doesn't exist, create it
                    repo.create_file(
                        path=filename,
                        message=f"Add {filename}",
                        content=content,
                        branch="main"
                    )
                    print(f"Created: {filename}")
                else:
                    raise
                    
        except Exception as e:
            print(f"Error updating {filename}: {e}")
            raise
    
    def _enable_pages(self, repo) -> str:
        """Enable GitHub Pages for the repository"""
        try:
            # Try to enable pages
            repo.create_pages_site(source={"branch": "main", "path": "/"})
            print(f"Enabled GitHub Pages")
        except GithubException as e:
            if e.status == 409:
                # Pages already enabled
                print("GitHub Pages already enabled")
            else:
                print(f"Error enabling pages: {e}")
        
        # Return pages URL
        pages_url = f"https://{self.username}.github.io/{repo.name}/"
        return pages_url
    
    def verify_repo_accessible(self, repo_url: str) -> bool:
        """Verify that a repo is accessible"""
        try:
            repo_name = repo_url.split('/')[-1]
            repo = self.user.get_repo(repo_name)
            return True
        except:
            return False
