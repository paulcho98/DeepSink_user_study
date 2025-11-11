#!/usr/bin/env python3
"""
GitHub Issues를 통해 수집된 사용자 연구 결과를 분석하는 스크립트 (시각화 없는 버전)

이 스크립트는:
1. GitHub Issues API를 사용해 사용자 연구 결과를 수집
2. JSON 데이터를 파싱하고 정리
3. 모델별 성능 비교 분석 (질문별)
4. 결과를 CSV와 JSON으로 저장
5. 기본 통계 제공 (matplotlib 없이)
"""

import json
import os
import csv
import requests
from datetime import datetime
from collections import defaultdict, Counter
import configparser
from typing import Dict, List, Any

class GitHubResultsCollector:
    def __init__(self, token: str, owner: str = "deep-overflow", repo: str = "InterGenEval_user_study"):
        """
        GitHub Issues 결과 수집기 초기화
        
        Args:
            token: GitHub Personal Access Token
            owner: Repository 소유자
            repo: Repository 이름
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        
    def collect_study_results(self) -> List[Dict[str, Any]]:
        """
        GitHub Issues에서 사용자 연구 결과를 수집
        
        Returns:
            List of parsed study results
        """
        print("🔍 Collecting user study results from GitHub Issues...")
        
        # Get issues with user-study-result label
        url = f"{self.base_url}/issues"
        params = {
            'labels': 'user-study-result',
            'state': 'all',
            'per_page': 100
        }
        
        all_results = []
        page = 1
        
        while True:
            params['page'] = page
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"❌ Error fetching issues: {response.status_code}")
                break
                
            issues = response.json()
            if not issues:
                break
                
            print(f"📄 Processing page {page} ({len(issues)} issues)...")
            
            for issue in issues:
                try:
                    result = self.parse_issue_result(issue)
                    if result:
                        all_results.append(result)
                except Exception as e:
                    print(f"⚠️ Error parsing issue #{issue['number']}: {e}")
                    
            page += 1
            
        print(f"✅ Collected {len(all_results)} valid study results")
        return all_results
    
    def parse_issue_result(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        GitHub Issue에서 사용자 연구 결과 파싱
        
        Args:
            issue: GitHub issue data
            
        Returns:
            Parsed study result data
        """
        body = issue['body']
        
        # Extract JSON data from markdown code block
        json_start = body.find('```json')
        json_end = body.find('```', json_start + 7)
        
        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON data found in issue body")
            
        json_str = body[json_start + 7:json_end].strip()
        
        try:
            result_data = json.loads(json_str)
            
            # Add GitHub metadata
            result_data['github_issue_number'] = issue['number']
            result_data['github_created_at'] = issue['created_at']
            result_data['github_url'] = issue['html_url']
            
            return result_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        수집된 결과 데이터 분석
        
        Args:
            results: List of study results
            
        Returns:
            Analysis summary
        """
        print("📊 Analyzing collected results...")
        
        question_names = [
            'interaction_accuracy',
            'entity_accuracy', 
            'temporal_consistency',
            'prompt_faithfulness',
            'overall_quality'
        ]
        
        analysis = {
            'total_participants': len(results),
            'total_comparisons': 0,
            'question_analyses': {},
            'demographics': defaultdict(list),
            'study_durations': [],
            'completion_times': []
        }
        
        # Initialize question analyses
        for question in question_names:
            analysis['question_analyses'][question] = {
                'model_comparisons': defaultdict(lambda: {'wins': 0, 'total': 0}),
                'comparison_sets': defaultdict(list)
            }
        
        for result in results:
            # Study duration
            duration_minutes = result.get('studyDuration', 0) / 1000 / 60
            analysis['study_durations'].append(duration_minutes)
            
            # Completion time
            analysis['completion_times'].append(result.get('timestamp'))
            
            # Demographics
            demographics = result.get('demographics', {})
            for key, value in demographics.items():
                analysis['demographics'][key].append(value)
            
            # Process responses
            responses = result.get('responses', {})
            for comparison_set, videos in responses.items():
                analysis['total_comparisons'] += len(videos)
                
                for video_id, response_data in videos.items():
                    # Handle different response formats
                    if isinstance(response_data, dict) and 'answers' in response_data:
                        # New multi-question format
                        answers = response_data['answers']
                        for question in question_names:
                            choice = answers.get(question)
                            if choice in ['A', 'B']:
                                self._process_choice(analysis['question_analyses'][question], 
                                                   comparison_set, choice, result, video_id, response_data)
                    elif isinstance(response_data, str):
                        # Legacy single choice format - map to overall_quality
                        choice = response_data
                        if choice in ['A', 'B']:
                            self._process_choice(analysis['question_analyses']['overall_quality'], 
                                               comparison_set, choice, result, video_id, {'choice': choice})
                    elif isinstance(response_data, dict) and 'choice' in response_data:
                        # Old object format - map to overall_quality
                        choice = response_data.get('choice')
                        if choice in ['A', 'B']:
                            self._process_choice(analysis['question_analyses']['overall_quality'], 
                                               comparison_set, choice, result, video_id, response_data)
        
        # Calculate win rates for all questions
        for question, q_analysis in analysis['question_analyses'].items():
            for model, stats in q_analysis['model_comparisons'].items():
                stats['win_rate'] = stats['wins'] / stats['total'] if stats['total'] > 0 else 0
                
        return analysis
    
    def _process_choice(self, question_analysis, comparison_set, choice, result, video_id, response_data):
        """Helper method to process a single choice"""
        models = comparison_set.split('_vs_')
        if len(models) == 2:
            chosen_model = models[0] if choice == 'A' else models[1]
            other_model = models[1] if choice == 'A' else models[0]
            
            # Record win for chosen model
            question_analysis['model_comparisons'][chosen_model]['wins'] += 1
            question_analysis['model_comparisons'][chosen_model]['total'] += 1
            question_analysis['model_comparisons'][other_model]['total'] += 1
            
            # Store comparison data
            question_analysis['comparison_sets'][comparison_set].append({
                'participant': result.get('participantId'),
                'video_id': video_id,
                'choice': choice,
                'chosen_model': chosen_model,
                'timestamp': response_data.get('timestamp') if isinstance(response_data, dict) else None
            })
    
    def print_analysis_summary(self, analysis: Dict[str, Any]):
        """분석 결과를 콘솔에 출력"""
        print("\n" + "="*60)
        print("📊 사용자 연구 분석 결과")
        print("="*60)
        
        print(f"\n📈 전체 통계:")
        print(f"   총 참가자 수: {analysis['total_participants']}")
        print(f"   총 비교 횟수: {analysis['total_comparisons']}")
        
        if analysis['study_durations']:
            avg_duration = sum(analysis['study_durations']) / len(analysis['study_durations'])
            print(f"   평균 연구 시간: {avg_duration:.1f}분")
        
        question_labels = {
            'interaction_accuracy': '상호작용 정확성',
            'entity_accuracy': '대상 정확성', 
            'temporal_consistency': '시간적 일관성',
            'prompt_faithfulness': '프롬프트 충실도',
            'overall_quality': '전반적 품질'
        }
        
        for question, label in question_labels.items():
            q_analysis = analysis['question_analyses'].get(question, {})
            model_comparisons = q_analysis.get('model_comparisons', {})
            
            if model_comparisons:
                print(f"\n🏆 {label} ({question}):")
                sorted_models = sorted(model_comparisons.items(), 
                                     key=lambda x: x[1]['win_rate'], reverse=True)
                
                for model, stats in sorted_models:
                    print(f"   {model}: {stats['win_rate']:.3f} ({stats['wins']}/{stats['total']})")
            else:
                print(f"\n🏆 {label} ({question}): 데이터 없음")
    
    def save_results(self, results: List[Dict[str, Any]], analysis: Dict[str, Any], output_dir: str = "github_analysis_output"):
        """
        결과를 다양한 형식으로 저장 (날짜별 폴더 구조)
        
        Args:
            results: Raw study results
            analysis: Analysis summary
            output_dir: Base output directory
        """
        # Create date-based output directory
        current_date = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H%M%S")
        
        date_output_dir = os.path.join(output_dir, current_date)
        final_output_dir = os.path.join(date_output_dir, f"github_analysis_{timestamp}")
        
        os.makedirs(final_output_dir, exist_ok=True)
        
        # Save raw results
        raw_file = os.path.join(final_output_dir, "raw_results.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Raw results saved to: {raw_file}")
        
        # Save analysis summary
        analysis_file = os.path.join(final_output_dir, "analysis_summary.json")
        with open(analysis_file, 'w', encoding='utf-8') as f:
            # Convert defaultdict to regular dict for JSON serialization
            analysis_json = json.loads(json.dumps(analysis, default=str))
            json.dump(analysis_json, f, indent=2, ensure_ascii=False)
        print(f"📊 Analysis summary saved to: {analysis_file}")
        
        # Save detailed CSV results
        self._save_detailed_csv(analysis, final_output_dir)
        
        print(f"\n📁 모든 결과가 저장됨: {final_output_dir}")
        
    def _save_detailed_csv(self, analysis: Dict[str, Any], output_dir: str):
        """Save detailed CSV results for each question"""
        question_labels = {
            'interaction_accuracy': '상호작용 정확성',
            'entity_accuracy': '대상 정확성', 
            'temporal_consistency': '시간적 일관성',
            'prompt_faithfulness': '프롬프트 충실도',
            'overall_quality': '전반적 품질'
        }
        
        # Combined summary CSV
        csv_file = os.path.join(output_dir, "model_comparison_summary.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Question', 'Question_Label', 'Model', 'Wins', 'Total_Comparisons', 'Win_Rate'])
            
            for question, label in question_labels.items():
                q_analysis = analysis['question_analyses'].get(question, {})
                model_comparisons = q_analysis.get('model_comparisons', {})
                
                for model, stats in model_comparisons.items():
                    writer.writerow([question, label, model, stats['wins'], stats['total'], f"{stats['win_rate']:.3f}"])
        
        print(f"📈 Detailed comparison saved to: {csv_file}")

def load_config(config_file='config.ini'):
    """설정 파일 로드"""
    config = configparser.ConfigParser()
    if os.path.exists(config_file):
        config.read(config_file)
        return config
    return None

def main():
    """
    메인 실행 함수
    """
    print("🚀 GitHub Issues User Study Results Collector (No Visualization)")
    print("=" * 70)
    
    # Try to load token from config
    token = None
    config = load_config()
    if config and 'github' in config:
        token = config['github'].get('token')
        if token == 'GITHUB_TOKEN_PLACEHOLDER':
            token = None
    
    if not token:
        token = input("🔑 GitHub Personal Access Token을 입력하세요: ").strip()
    
    if not token:
        print("❌ GitHub token이 필요합니다.")
        return
    
    try:
        # Initialize collector
        collector = GitHubResultsCollector(token)
        
        # Collect results
        results = collector.collect_study_results()
        
        if not results:
            print("❌ 수집된 결과가 없습니다.")
            return
        
        # Analyze results
        analysis = collector.analyze_results(results)
        
        # Print summary
        collector.print_analysis_summary(analysis)
        
        # Save results
        collector.save_results(results, analysis)
        
        print("\n✅ 분석 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()