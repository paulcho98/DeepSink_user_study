#!/usr/bin/env python3
"""
GitHub Issues를 통해 수집된 사용자 연구 결과를 분석하는 스크립트

이 스크립트는:
1. GitHub Issues API를 사용해 사용자 연구 결과를 수집
2. JSON 데이터를 파싱하고 정리
3. 모델별 성능 비교 분석
4. 결과를 CSV와 JSON으로 저장
5. 기본 통계 및 시각화 제공
"""

import json
import os
import csv
import requests
from datetime import datetime
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
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
        
        analysis = {
            'total_participants': len(results),
            'total_comparisons': 0,
            'model_comparisons': defaultdict(lambda: {'wins': 0, 'total': 0}),
            'comparison_sets': defaultdict(list),
            'demographics': defaultdict(list),
            'study_durations': [],
            'completion_times': []
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
                
                for video_id, choice_data in videos.items():
                    # Handle both string and object formats for choice data
                    if isinstance(choice_data, str):
                        choice = choice_data
                    elif isinstance(choice_data, dict):
                        choice = choice_data.get('choice')
                    else:
                        continue
                        
                    if choice in ['A', 'B']:
                        # Extract model names from comparison set
                        models = comparison_set.split('_vs_')
                        if len(models) == 2:
                            chosen_model = models[0] if choice == 'A' else models[1]
                            other_model = models[1] if choice == 'A' else models[0]
                            
                            # Record win for chosen model
                            analysis['model_comparisons'][chosen_model]['wins'] += 1
                            analysis['model_comparisons'][chosen_model]['total'] += 1
                            analysis['model_comparisons'][other_model]['total'] += 1
                            
                            # Store comparison data
                            analysis['comparison_sets'][comparison_set].append({
                                'participant': result.get('participantId'),
                                'video_id': video_id,
                                'choice': choice,
                                'chosen_model': chosen_model,
                                'timestamp': choice_data.get('timestamp') if isinstance(choice_data, dict) else None
                            })
        
        # Calculate win rates
        for model, stats in analysis['model_comparisons'].items():
            stats['win_rate'] = stats['wins'] / stats['total'] if stats['total'] > 0 else 0
            
        return analysis
    
    def save_results(self, results: List[Dict[str, Any]], analysis: Dict[str, Any], output_dir: str = "github_analysis_output"):
        """
        결과를 다양한 형식으로 저장
        
        Args:
            results: Raw study results
            analysis: Analysis summary
            output_dir: Output directory
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw results
        raw_file = os.path.join(output_dir, f"raw_results_{timestamp}.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Raw results saved to: {raw_file}")
        
        # Save analysis summary
        analysis_file = os.path.join(output_dir, f"analysis_summary_{timestamp}.json")
        with open(analysis_file, 'w', encoding='utf-8') as f:
            # Convert defaultdict to regular dict for JSON serialization
            analysis_json = json.loads(json.dumps(analysis, default=str))
            json.dump(analysis_json, f, indent=2, ensure_ascii=False)
        print(f"📊 Analysis summary saved to: {analysis_file}")
        
        # Save model comparison CSV
        csv_file = os.path.join(output_dir, f"model_comparison_{timestamp}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Model', 'Wins', 'Total_Comparisons', 'Win_Rate'])
            
            for model, stats in analysis['model_comparisons'].items():
                writer.writerow([model, stats['wins'], stats['total'], f"{stats['win_rate']:.3f}"])
        print(f"📈 Model comparison saved to: {csv_file}")
        
        # Create visualizations
        self.create_visualizations(analysis, output_dir, timestamp)
        
    def create_visualizations(self, analysis: Dict[str, Any], output_dir: str, timestamp: str):
        """
        결과 시각화 생성
        
        Args:
            analysis: Analysis data
            output_dir: Output directory
            timestamp: Timestamp for file naming
        """
        plt.style.use('seaborn-v0_8')
        
        # Model win rate comparison
        models = list(analysis['model_comparisons'].keys())
        win_rates = [analysis['model_comparisons'][model]['win_rate'] for model in models]
        total_comps = [analysis['model_comparisons'][model]['total'] for model in models]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Win rate bar chart
        bars = ax1.bar(models, win_rates, color='skyblue', alpha=0.8)
        ax1.set_title('Model Win Rates', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Win Rate')
        ax1.set_ylim(0, 1)
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, rate in zip(bars, win_rates):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{rate:.3f}', ha='center', va='bottom')
        
        # Total comparisons bar chart
        bars2 = ax2.bar(models, total_comps, color='lightcoral', alpha=0.8)
        ax2.set_title('Total Comparisons per Model', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Number of Comparisons')
        ax2.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, count in zip(bars2, total_comps):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{count}', ha='center', va='bottom')
        
        plt.tight_layout()
        plot_file = os.path.join(output_dir, f"model_comparison_{timestamp}.png")
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Visualization saved to: {plot_file}")
        
        # Study duration histogram
        if analysis['study_durations']:
            plt.figure(figsize=(10, 6))
            plt.hist(analysis['study_durations'], bins=15, color='lightgreen', alpha=0.7, edgecolor='black')
            plt.title('Study Duration Distribution', fontsize=14, fontweight='bold')
            plt.xlabel('Duration (minutes)')
            plt.ylabel('Number of Participants')
            plt.grid(True, alpha=0.3)
            
            # Add statistics
            mean_duration = sum(analysis['study_durations']) / len(analysis['study_durations'])
            plt.axvline(mean_duration, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_duration:.1f} min')
            plt.legend()
            
            duration_plot = os.path.join(output_dir, f"study_duration_{timestamp}.png")
            plt.savefig(duration_plot, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"⏱️ Duration plot saved to: {duration_plot}")

def main():
    """
    메인 실행 함수
    """
    print("🚀 GitHub Issues User Study Results Collector")
    print("=" * 50)
    
    # GitHub token - 실제 사용 시 환경변수나 설정파일에서 읽어오기
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
        print("\n📊 분석 요약:")
        print(f"   총 참가자 수: {analysis['total_participants']}")
        print(f"   총 비교 횟수: {analysis['total_comparisons']}")
        print(f"   평균 연구 시간: {sum(analysis['study_durations'])/len(analysis['study_durations']):.1f}분")
        
        print("\n🏆 모델별 승률:")
        for model, stats in sorted(analysis['model_comparisons'].items(), 
                                 key=lambda x: x[1]['win_rate'], reverse=True):
            print(f"   {model}: {stats['win_rate']:.3f} ({stats['wins']}/{stats['total']})")
        
        # Save results
        collector.save_results(results, analysis)
        
        print("\n✅ 분석 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()