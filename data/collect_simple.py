#!/usr/bin/env python3
"""
간단한 GitHub Issues 결과 수집 스크립트

사용법:
1. config.ini 파일에서 GITHUB_TOKEN_PLACEHOLDER를 실제 토큰으로 변경
2. python collect_simple.py 실행

또는

python collect_simple.py --token YOUR_GITHUB_TOKEN
"""

import json
import os
import requests
import argparse
import configparser
from datetime import datetime
from collections import defaultdict

def load_config(config_file='config.ini'):
    """설정 파일 로드"""
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def collect_issues(token, owner='deep-overflow', repo='InterGenEval_user_study'):
    """GitHub Issues에서 사용자 연구 결과 수집"""
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {
        'labels': 'user-study-result',
        'state': 'all',
        'per_page': 100
    }
    
    print("🔍 Collecting issues from GitHub...")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        return []
    
    issues = response.json()
    print(f"✅ Found {len(issues)} issues")
    
    results = []
    for issue in issues:
        try:
            result = parse_issue(issue)
            if result:
                results.append(result)
        except Exception as e:
            print(f"⚠️ Error parsing issue #{issue['number']}: {e}")
    
    return results

def parse_issue(issue):
    """Issue에서 JSON 데이터 추출"""
    body = issue['body']
    
    # Find JSON block
    start = body.find('```json')
    end = body.find('```', start + 7)
    
    if start == -1 or end == -1:
        return None
    
    json_str = body[start + 7:end].strip()
    
    try:
        data = json.loads(json_str)
        data['github_issue'] = issue['number']
        data['github_url'] = issue['html_url']
        return data
    except:
        return None

def analyze_results(results):
    """간단한 결과 분석"""
    print("\n📊 분석 결과:")
    print(f"총 참가자: {len(results)}")
    
    if not results:
        return
    
    # 모델별 승수 계산 (질문별로)
    question_names = [
        'interaction_accuracy',
        'entity_accuracy', 
        'temporal_consistency',
        'prompt_faithfulness',
        'overall_quality'
    ]
    
    question_labels = {
        'interaction_accuracy': '상호작용 정확성',
        'entity_accuracy': '대상 정확성', 
        'temporal_consistency': '시간적 일관성',
        'prompt_faithfulness': '프롬프트 충실도',
        'overall_quality': '전반적 품질'
    }
    
    for question_name in question_names:
        print(f"\n🏆 {question_labels[question_name]} ({question_name}):")
        model_wins = defaultdict(int)
        model_total = defaultdict(int)
        
        for result in results:
            responses = result.get('responses', {})
            for comparison_set, videos in responses.items():
                models = comparison_set.split('_vs_')
                if len(models) != 2:
                    continue
                    
                for video_file, response_data in videos.items():
                    choice = None
                    
                    # Handle different response formats
                    if isinstance(response_data, dict) and 'answers' in response_data:
                        # New multi-question format
                        choice = response_data['answers'].get(question_name)
                    elif isinstance(response_data, str):
                        # Legacy single choice format - map to overall_quality
                        if question_name == 'overall_quality':
                            choice = response_data
                    elif isinstance(response_data, dict) and 'choice' in response_data:
                        # Old object format - map to overall_quality
                        if question_name == 'overall_quality':
                            choice = response_data.get('choice')
                    
                    if choice in ['A', 'B']:
                        chosen = models[0] if choice == 'A' else models[1]
                        other = models[1] if choice == 'A' else models[0]
                        
                        model_wins[chosen] += 1
                        model_total[chosen] += 1
                        model_total[other] += 1
        
        # Print results for this question
        for model in sorted(model_total.keys()):
            if model_total[model] > 0:
                win_rate = model_wins[model] / model_total[model]
                print(f"  {model}: {win_rate:.3f} ({model_wins[model]}/{model_total[model]})")
        
        if not model_total:
            print("  데이터 없음")

def main():
    parser = argparse.ArgumentParser(description='Collect GitHub Issues user study results')
    parser.add_argument('--token', help='GitHub Personal Access Token')
    parser.add_argument('--config', default='config.ini', help='Config file path')
    args = parser.parse_args()
    
    # Get token
    token = args.token
    if not token:
        try:
            config = load_config(args.config)
            token = config['github']['token']
            if token == 'GITHUB_TOKEN_PLACEHOLDER':
                token = None
        except:
            pass
    
    if not token:
        print("❌ GitHub token이 필요합니다.")
        print("사용법:")
        print("1. config.ini에서 토큰 설정, 또는")
        print("2. python collect_simple.py --token YOUR_TOKEN")
        return
    
    # Collect and analyze
    results = collect_issues(token)
    
    if results:
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"collected_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 결과 저장됨: {filename}")
        
        # Analyze
        analyze_results(results)
    else:
        print("❌ 수집된 결과가 없습니다.")

if __name__ == "__main__":
    main()