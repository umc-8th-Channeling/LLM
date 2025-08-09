import os
import sys
import json
import google.generativeai as genai
from github import Github
from typing import List, Dict, Any


class GeminiPRReviewer:
    def __init__(self):
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.pr_number = int(os.environ.get('PR_NUMBER', 0))
        
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다")
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN이 설정되지 않았습니다")
        if not self.pr_number:
            raise ValueError("PR_NUMBER가 설정되지 않았습니다")
        
        # Initialize Gemini
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Initialize GitHub
        self.github = Github(self.github_token)
        self.repo = self._get_repository()
        self.pr = self.repo.get_pull(self.pr_number)
    
    def _get_repository(self) -> Any:
        """GitHub 레포지토리 객체 가져오기"""
        # GitHub Actions 환경변수에서 레포지토리 정보 추출
        repo_name = os.environ.get('GITHUB_REPOSITORY')  # owner/repo 형식
        if not repo_name:
            raise ValueError("GITHUB_REPOSITORY가 설정되지 않았습니다")
        return self.github.get_repo(repo_name)
    
    def get_pr_diff(self) -> Dict[str, Any]:
        """PR의 변경사항 가져오기"""
        files_changed = []
        total_additions = 0
        total_deletions = 0
        
        # PR의 파일 변경사항 가져오기
        for file in self.pr.get_files():
            # 파일 크기 제한 (너무 큰 파일은 스킵)
            if file.additions + file.deletions > 500:
                files_changed.append({
                    'filename': file.filename,
                    'status': file.status,
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'patch': f"[파일이 너무 큼: 추가 {file.additions}줄, 삭제 {file.deletions}줄]"
                })
            else:
                files_changed.append({
                    'filename': file.filename,
                    'status': file.status,
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'patch': file.patch if hasattr(file, 'patch') and file.patch else ''
                })
            
            total_additions += file.additions
            total_deletions += file.deletions
        
        return {
            'title': self.pr.title,
            'body': self.pr.body or '',
            'files_changed': files_changed,
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'num_files': len(files_changed)
        }
    
    def create_review_prompt(self, pr_info: Dict[str, Any]) -> str:
        """Gemini에게 보낼 리뷰 프롬프트 생성"""
        prompt = f"""
You are an experienced code reviewer. Please review the following Pull Request and provide constructive feedback.

**PR Title:** {pr_info['title']}
**PR Description:** {pr_info['body']}
**Summary:** {pr_info['num_files']} files changed, +{pr_info['total_additions']} additions, -{pr_info['total_deletions']} deletions

**Changed Files:**
"""
        
        for file in pr_info['files_changed']:
            prompt += f"\n### {file['filename']} ({file['status']})\n"
            prompt += f"Changes: +{file['additions']}, -{file['deletions']}\n"
            if file['patch']:
                prompt += f"```diff\n{file['patch']}\n```\n"
        
        prompt += """

Please provide a code review with the following structure:

1. **Overall Assessment**: Brief summary of the changes
2. **Strengths**: What's done well
3. **Issues Found**: Any bugs, potential issues, or concerns (if any)
4. **Suggestions**: Improvements or recommendations
5. **Security Check**: Any security concerns (if applicable)

Use Korean for your response. Be constructive and specific. If the code looks good, say so.
Format your response in Markdown.
"""
        
        return prompt
    
    def get_gemini_review(self, prompt: str) -> str:
        """Gemini API를 통해 코드 리뷰 받기"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"❌ Gemini API 호출 실패: {str(e)}"
    
    def post_review_comment(self, review_content: str):
        """PR에 리뷰 코멘트 게시"""
        comment_body = f"""## 🤖 Gemini AI 코드 리뷰

{review_content}

---
*이 리뷰는 Gemini AI가 자동으로 생성했습니다. 참고용으로만 활용해주세요.*
"""
        
        # PR에 코멘트 추가
        self.pr.create_issue_comment(comment_body)
        print(f"✅ PR #{self.pr_number}에 리뷰가 게시되었습니다")
    
    def run(self):
        """메인 실행 함수"""
        try:
            print(f"📋 PR #{self.pr_number} 정보를 가져오는 중...")
            pr_info = self.get_pr_diff()
            
            # 변경사항이 너무 크면 스킵
            if pr_info['total_additions'] + pr_info['total_deletions'] > 2000:
                print("⚠️ PR이 자동 리뷰하기에 너무 큽니다")
                self.post_review_comment(
                    "⚠️ 이 PR은 자동 리뷰하기에 너무 큽니다 (2000줄 이상 변경). "
                    "수동 리뷰를 권장합니다."
                )
                return
            
            print("🤖 Gemini에게 리뷰를 요청하는 중...")
            prompt = self.create_review_prompt(pr_info)
            review = self.get_gemini_review(prompt)
            
            print("📝 PR에 리뷰를 게시하는 중...")
            self.post_review_comment(review)
            
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    reviewer = GeminiPRReviewer()
    reviewer.run()