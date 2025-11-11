#!/usr/bin/env python3
"""
GitHub Issues를 통해 수집된 사용자 연구 결과를 분석하고 시각화하는 완전한 스크립트

이 스크립트는:
1. GitHub Issues API를 사용해 사용자 연구 결과를 수집
2. JSON 데이터를 파싱하고 정리
3. 질문별 모델 성능 비교 분석
4. 결과를 CSV와 JSON으로 저장
5. 고급 시각화 및 차트 생성
6. 상세한 통계 분석 제공
"""

import json
import os
import csv
import requests
from datetime import datetime
from collections import defaultdict, Counter
import configparser
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# 한글 폰트 설정
plt.rcParams['font.family'] = ['Arial Unicode MS', 'DejaVu Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

class GitHubResultsVisualizer:
    def __init__(self, token: str, owner: str = "deep-overflow", repo: str = "InterGenEval_user_study"):
        """
        GitHub Issues 결과 수집 및 시각화기 초기화
        
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
        
        # 질문 정보
        self.question_names = [
            'interaction_accuracy',
            'entity_accuracy', 
            'temporal_consistency',
            'prompt_faithfulness',
            'overall_quality'
        ]
        
        self.question_labels = {
            'interaction_accuracy': '상호작용 정확성',
            'entity_accuracy': '대상 정확성', 
            'temporal_consistency': '시간적 일관성',
            'prompt_faithfulness': '프롬프트 충실도',
            'overall_quality': '전반적 품질'
        }
        
        # 색상 팔레트
        self.colors = sns.color_palette("husl", n_colors=8)
        
    def collect_study_results(self) -> List[Dict[str, Any]]:
        """GitHub Issues에서 사용자 연구 결과를 수집"""
        print("🔍 Collecting user study results from GitHub Issues...")
        
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
        """GitHub Issue에서 사용자 연구 결과 파싱"""
        body = issue['body']
        
        # Extract JSON data from markdown code block
        json_start = body.find('```json')
        json_end = body.find('```', json_start + 7)
        
        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON data found in issue body")
            
        json_str = body[json_start + 7:json_end].strip()
        
        try:
            result_data = json.loads(json_str)
            result_data['github_issue_number'] = issue['number']
            result_data['github_created_at'] = issue['created_at']
            result_data['github_url'] = issue['html_url']
            return result_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """수집된 결과 데이터 분석"""
        print("📊 Analyzing collected results...")
        
        analysis = {
            'total_participants': len(results),
            'total_comparisons': 0,
            'question_analyses': {},
            'demographics': defaultdict(list),
            'study_durations': [],
            'completion_times': [],
            'raw_comparison_data': []
        }
        
        # Initialize question analyses
        for question in self.question_names:
            analysis['question_analyses'][question] = {
                'model_comparisons': defaultdict(lambda: {'wins': 0, 'total': 0}),
                'comparison_sets': defaultdict(list),
                'participant_choices': []
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
                        for question in self.question_names:
                            choice = answers.get(question)
                            if choice in ['A', 'B']:
                                self._process_choice(analysis['question_analyses'][question], 
                                                   comparison_set, choice, result, video_id, response_data)
                    elif isinstance(response_data, str):
                        # Legacy single choice format
                        choice = response_data
                        if choice in ['A', 'B']:
                            self._process_choice(analysis['question_analyses']['overall_quality'], 
                                               comparison_set, choice, result, video_id, {'choice': choice})
                    elif isinstance(response_data, dict) and 'choice' in response_data:
                        # Old object format
                        choice = response_data.get('choice')
                        if choice in ['A', 'B']:
                            self._process_choice(analysis['question_analyses']['overall_quality'], 
                                               comparison_set, choice, result, video_id, response_data)
        
        # Calculate win rates
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
            
            # Store detailed data
            question_analysis['participant_choices'].append({
                'participant': result.get('participantId'),
                'comparison_set': comparison_set,
                'video_id': video_id,
                'choice': choice,
                'chosen_model': chosen_model,
                'model_a': models[0],
                'model_b': models[1],
                'timestamp': response_data.get('timestamp') if isinstance(response_data, dict) else None
            })
    
    def create_comprehensive_visualizations(self, analysis: Dict[str, Any], output_dir: str, timestamp: str):
        """포괄적인 시각화 생성"""
        print("🎨 Creating comprehensive visualizations...")
        
        # Set style
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # 1. 질문별 모델 성능 히트맵
        self._create_performance_heatmap(analysis, output_dir, timestamp)
        
        # 2. 질문별 상세 바 차트
        self._create_detailed_bar_charts(analysis, output_dir, timestamp)
        
        # 3. 모델 간 직접 비교 매트릭스
        self._create_model_comparison_matrix(analysis, output_dir, timestamp)
        
        # 4. 연구 참여 통계
        self._create_participation_stats(analysis, output_dir, timestamp)
        
        # 5. 종합 대시보드
        self._create_dashboard(analysis, output_dir, timestamp)
        
        print("✅ All visualizations created!")
    
    def _create_performance_heatmap(self, analysis: Dict[str, Any], output_dir: str, timestamp: str):
        """질문별 모델 성능 히트맵 생성"""
        # 데이터 준비
        models = set()
        for q_analysis in analysis['question_analyses'].values():
            models.update(q_analysis['model_comparisons'].keys())
        
        models = sorted(list(models))
        
        # 히트맵 데이터 생성
        heatmap_data = []
        for question in self.question_names:
            row = []
            q_analysis = analysis['question_analyses'][question]
            for model in models:
                win_rate = q_analysis['model_comparisons'].get(model, {}).get('win_rate', 0)
                row.append(win_rate)
            heatmap_data.append(row)
        
        # 히트맵 생성
        fig, ax = plt.subplots(figsize=(12, 8))
        
        im = ax.imshow(heatmap_data, cmap='RdYlBu_r', aspect='auto', vmin=0, vmax=1)
        
        # 축 설정
        ax.set_xticks(range(len(models)))
        ax.set_yticks(range(len(self.question_names)))
        ax.set_xticklabels(models, rotation=45, ha='right')
        ax.set_yticklabels([self.question_labels[q] for q in self.question_names])
        
        # 값 표시
        for i in range(len(self.question_names)):
            for j in range(len(models)):
                value = heatmap_data[i][j]
                text = ax.text(j, i, f'{value:.2f}', ha='center', va='center',
                             color='white' if value > 0.5 else 'black', fontweight='bold')
        
        # 컬러바
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('승률 (Win Rate)', rotation=270, labelpad=20)
        
        plt.title('질문별 모델 성능 히트맵\nModel Performance Heatmap by Question', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.tight_layout()
        
        heatmap_file = os.path.join(output_dir, f"performance_heatmap_{timestamp}.png")
        plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"🔥 Performance heatmap saved to: {heatmap_file}")
    
    def _create_detailed_bar_charts(self, analysis: Dict[str, Any], output_dir: str, timestamp: str):
        """질문별 상세 바 차트 생성"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        axes = axes.flatten()
        
        for i, question in enumerate(self.question_names):
            ax = axes[i]
            q_analysis = analysis['question_analyses'][question]
            model_comparisons = q_analysis['model_comparisons']
            
            if model_comparisons:
                models = list(model_comparisons.keys())
                win_rates = [model_comparisons[model]['win_rate'] for model in models]
                totals = [model_comparisons[model]['total'] for model in models]
                
                # 바 차트 생성
                bars = ax.bar(models, win_rates, color=self.colors[:len(models)], alpha=0.8)
                
                # 값 라벨 추가
                for bar, win_rate, total in zip(bars, win_rates, totals):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                           f'{win_rate:.2f}\n({total})', ha='center', va='bottom', fontweight='bold')
                
                ax.set_title(f'{self.question_labels[question]}', fontsize=12, fontweight='bold')
                ax.set_ylabel('승률 (Win Rate)')
                ax.set_ylim(0, 1.1)
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, alpha=0.3)
            else:
                ax.text(0.5, 0.5, '데이터 없음', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'{self.question_labels[question]}', fontsize=12, fontweight='bold')
        
        # 마지막 서브플롯 숨기기
        axes[-1].set_visible(False)
        
        plt.suptitle('질문별 모델 성능 상세 분석\nDetailed Model Performance by Question', 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        detailed_file = os.path.join(output_dir, f"detailed_performance_{timestamp}.png")
        plt.savefig(detailed_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Detailed performance charts saved to: {detailed_file}")
    
    def _create_model_comparison_matrix(self, analysis: Dict[str, Any], output_dir: str, timestamp: str):
        """모델 간 직접 비교 매트릭스 생성"""
        # 모델별 전체 승률 계산
        overall_performance = {}
        
        for question, q_analysis in analysis['question_analyses'].items():
            for model, stats in q_analysis['model_comparisons'].items():
                if model not in overall_performance:
                    overall_performance[model] = {'wins': 0, 'total': 0}
                overall_performance[model]['wins'] += stats['wins']
                overall_performance[model]['total'] += stats['total']
        
        # 승률 계산
        for model in overall_performance:
            stats = overall_performance[model]
            stats['win_rate'] = stats['wins'] / stats['total'] if stats['total'] > 0 else 0
        
        # 정렬
        sorted_models = sorted(overall_performance.items(), 
                             key=lambda x: x[1]['win_rate'], reverse=True)
        
        # 시각화
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # 전체 승률
        models = [item[0] for item in sorted_models]
        win_rates = [item[1]['win_rate'] for item in sorted_models]
        totals = [item[1]['total'] for item in sorted_models]
        
        bars1 = ax1.bar(models, win_rates, color=self.colors[:len(models)], alpha=0.8)
        
        for bar, win_rate, total in zip(bars1, win_rates, totals):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{win_rate:.3f}\n({total})', ha='center', va='bottom', fontweight='bold')
        
        ax1.set_title('전체 모델 성능 순위\nOverall Model Performance Ranking', fontweight='bold')
        ax1.set_ylabel('전체 승률 (Overall Win Rate)')
        ax1.set_ylim(0, 1.1)
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)
        
        # 질문별 성능 레이더 차트 (상위 4개 모델)
        top_models = models[:4]
        angles = np.linspace(0, 2 * np.pi, len(self.question_names), endpoint=False)
        angles = np.concatenate((angles, [angles[0]]))  # 원형으로 만들기
        
        ax2 = plt.subplot(122, projection='polar')
        
        for model in top_models:
            values = []
            for question in self.question_names:
                q_analysis = analysis['question_analyses'][question]
                win_rate = q_analysis['model_comparisons'].get(model, {}).get('win_rate', 0)
                values.append(win_rate)
            values += [values[0]]  # 원형으로 만들기
            
            ax2.plot(angles, values, 'o-', linewidth=2, label=model)
            ax2.fill(angles, values, alpha=0.25)
        
        ax2.set_xticks(angles[:-1])
        ax2.set_xticklabels([self.question_labels[q] for q in self.question_names])
        ax2.set_ylim(0, 1)
        ax2.set_title('상위 모델 질문별 성능\nTop Models Performance by Question', 
                     fontweight='bold', pad=20)
        ax2.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        plt.tight_layout()
        
        comparison_file = os.path.join(output_dir, f"model_comparison_{timestamp}.png")
        plt.savefig(comparison_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"🎯 Model comparison matrix saved to: {comparison_file}")
    
    def _create_participation_stats(self, analysis: Dict[str, Any], output_dir: str, timestamp: str):
        """연구 참여 통계 생성"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. 연구 소요 시간 분포
        durations = analysis['study_durations']
        if durations:
            ax1.hist(durations, bins=min(10, len(durations)), color='skyblue', alpha=0.7, edgecolor='black')
            ax1.axvline(np.mean(durations), color='red', linestyle='--', 
                       label=f'평균: {np.mean(durations):.1f}분')
            ax1.set_title('연구 소요 시간 분포\nStudy Duration Distribution')
            ax1.set_xlabel('시간 (분)')
            ax1.set_ylabel('참가자 수')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # 2. 일별 참여 현황
        completion_times = [datetime.fromisoformat(t.replace('Z', '+00:00')) for t in analysis['completion_times'] if t]
        if completion_times:
            dates = [t.date() for t in completion_times]
            date_counts = Counter(dates)
            
            ax2.bar(range(len(date_counts)), list(date_counts.values()), color='lightgreen', alpha=0.7)
            ax2.set_title('일별 참여 현황\nDaily Participation')
            ax2.set_xlabel('날짜')
            ax2.set_ylabel('참가자 수')
            ax2.set_xticks(range(len(date_counts)))
            ax2.set_xticklabels([d.strftime('%m/%d') for d in date_counts.keys()], rotation=45)
            ax2.grid(True, alpha=0.3)
        
        # 3. 비교 세트별 참여도
        comparison_counts = defaultdict(int)
        for q_analysis in analysis['question_analyses'].values():
            for choice_data in q_analysis['participant_choices']:
                comparison_counts[choice_data['comparison_set']] += 1
        
        if comparison_counts:
            comparison_names = list(comparison_counts.keys())
            comparison_values = list(comparison_counts.values())
            
            ax3.barh(range(len(comparison_names)), comparison_values, color='orange', alpha=0.7)
            ax3.set_title('비교 세트별 참여도\nParticipation by Comparison Set')
            ax3.set_xlabel('평가 횟수')
            ax3.set_yticks(range(len(comparison_names)))
            ax3.set_yticklabels([name.replace('_vs_', ' vs ') for name in comparison_names])
            ax3.grid(True, alpha=0.3)
        
        # 4. 전체 통계 요약
        ax4.axis('off')
        stats_text = f"""
        📊 연구 참여 통계 요약
        
        총 참가자 수: {analysis['total_participants']}명
        총 평가 횟수: {analysis['total_comparisons']}회
        평균 연구 시간: {np.mean(durations):.1f}분
        
        질문별 데이터:
        """
        
        for question in self.question_names:
            q_analysis = analysis['question_analyses'][question]
            total_responses = len(q_analysis['participant_choices'])
            stats_text += f"  • {self.question_labels[question]}: {total_responses}개 응답\n"
        
        ax4.text(0.1, 0.7, stats_text, transform=ax4.transAxes, fontsize=12,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout()
        
        stats_file = os.path.join(output_dir, f"participation_stats_{timestamp}.png")
        plt.savefig(stats_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📈 Participation statistics saved to: {stats_file}")
    
    def _create_dashboard(self, analysis: Dict[str, Any], output_dir: str, timestamp: str):
        """종합 대시보드 생성"""
        fig = plt.figure(figsize=(20, 12))
        
        # 메인 제목
        fig.suptitle('비디오 생성 모델 사용자 연구 결과 대시보드\nVideo Generation Model User Study Results Dashboard', 
                    fontsize=20, fontweight='bold')
        
        # 레이아웃 설정
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
        
        # 1. 전체 모델 순위 (상단 좌측)
        ax1 = fig.add_subplot(gs[0, :2])
        overall_performance = {}
        
        for question, q_analysis in analysis['question_analyses'].items():
            for model, stats in q_analysis['model_comparisons'].items():
                if model not in overall_performance:
                    overall_performance[model] = {'wins': 0, 'total': 0}
                overall_performance[model]['wins'] += stats['wins']
                overall_performance[model]['total'] += stats['total']
        
        for model in overall_performance:
            stats = overall_performance[model]
            stats['win_rate'] = stats['wins'] / stats['total'] if stats['total'] > 0 else 0
        
        sorted_models = sorted(overall_performance.items(), key=lambda x: x[1]['win_rate'], reverse=True)
        models = [item[0] for item in sorted_models]
        win_rates = [item[1]['win_rate'] for item in sorted_models]
        
        bars = ax1.bar(models, win_rates, color=self.colors[:len(models)], alpha=0.8)
        ax1.set_title('전체 모델 성능 순위', fontweight='bold')
        ax1.set_ylabel('승률')
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. 핵심 통계 (상단 우측)
        ax2 = fig.add_subplot(gs[0, 2:])
        ax2.axis('off')
        
        key_stats = f"""
        📊 핵심 통계
        
        • 총 참가자: {analysis['total_participants']}명
        • 총 평가: {analysis['total_comparisons']}회
        • 평균 소요시간: {np.mean(analysis['study_durations']):.1f}분
        
        🏆 최고 성능 모델:
        • {models[0]}: {win_rates[0]:.3f}
        
        📝 활용 가능한 데이터:
        • 5개 질문별 세부 분석
        • 모델간 직접 비교
        • 시간대별 참여 패턴
        """
        
        ax2.text(0.05, 0.95, key_stats, transform=ax2.transAxes, fontsize=12,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        # 3. 질문별 최고 성능 모델 (중단)
        for i, question in enumerate(self.question_names):
            ax = fig.add_subplot(gs[1, i%4]) if i < 4 else fig.add_subplot(gs[2, (i-4)%4])
            
            q_analysis = analysis['question_analyses'][question]
            model_comparisons = q_analysis['model_comparisons']
            
            if model_comparisons:
                top_model = max(model_comparisons.items(), key=lambda x: x[1]['win_rate'])
                model_name, stats = top_model
                
                # 도넛 차트
                sizes = [stats['wins'], stats['total'] - stats['wins']]
                colors = ['#ff9999', '#66b3ff']
                
                wedges, texts = ax.pie(sizes, colors=colors, startangle=90)
                
                # 가운데 원 추가 (도넛 효과)
                centre_circle = plt.Circle((0,0), 0.70, fc='white')
                ax.add_artist(centre_circle)
                
                # 중앙에 정보 표시
                ax.text(0, 0.1, model_name, ha='center', va='center', fontweight='bold', fontsize=10)
                ax.text(0, -0.1, f'{stats["win_rate"]:.3f}', ha='center', va='center', fontsize=12)
                
                ax.set_title(f'{self.question_labels[question]}', fontsize=10, fontweight='bold')
        
        # 범례 추가
        legend_ax = fig.add_subplot(gs[2, 3])
        legend_ax.axis('off')
        legend_text = """
        📋 차트 범례
        
        🟠 승리
        🔵 패배
        
        각 도넛 차트는 해당 
        질문에서 최고 성능을 
        보인 모델을 표시
        """
        
        legend_ax.text(0.1, 0.8, legend_text, transform=legend_ax.transAxes, fontsize=10,
                      verticalalignment='top', fontfamily='monospace',
                      bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        
        dashboard_file = os.path.join(output_dir, f"comprehensive_dashboard_{timestamp}.png")
        plt.savefig(dashboard_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"🎯 Comprehensive dashboard saved to: {dashboard_file}")
    
    def save_results(self, results: List[Dict[str, Any]], analysis: Dict[str, Any], output_dir: str = "github_analysis_output"):
        """결과를 다양한 형식으로 저장하고 시각화 생성"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 기본 결과 저장
        raw_file = os.path.join(output_dir, f"raw_results_{timestamp}.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Raw results saved to: {raw_file}")
        
        analysis_file = os.path.join(output_dir, f"analysis_summary_{timestamp}.json")
        with open(analysis_file, 'w', encoding='utf-8') as f:
            analysis_json = json.loads(json.dumps(analysis, default=str))
            json.dump(analysis_json, f, indent=2, ensure_ascii=False)
        print(f"📊 Analysis summary saved to: {analysis_file}")
        
        # 시각화 생성
        self.create_comprehensive_visualizations(analysis, output_dir, timestamp)
        
        print(f"\n🎉 Complete analysis package saved to: {output_dir}")

def load_config(config_file='config.ini'):
    """설정 파일 로드"""
    config = configparser.ConfigParser()
    if os.path.exists(config_file):
        config.read(config_file)
        return config
    return None

def main():
    """메인 실행 함수"""
    print("🚀 GitHub Issues User Study Results Visualizer")
    print("=" * 60)
    
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
        # Initialize visualizer
        visualizer = GitHubResultsVisualizer(token)
        
        # Collect results
        results = visualizer.collect_study_results()
        
        if not results:
            print("❌ 수집된 결과가 없습니다.")
            return
        
        # Analyze results
        analysis = visualizer.analyze_results(results)
        
        # Print summary
        print("\n" + "="*60)
        print("📊 분석 요약:")
        print(f"   총 참가자 수: {analysis['total_participants']}")
        print(f"   총 비교 횟수: {analysis['total_comparisons']}")
        if analysis['study_durations']:
            print(f"   평균 연구 시간: {np.mean(analysis['study_durations']):.1f}분")
        
        # Save results and create visualizations
        visualizer.save_results(results, analysis)
        
        print("\n✅ 분석 및 시각화 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()