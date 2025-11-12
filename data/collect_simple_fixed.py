#!/usr/bin/env python3
"""
개선된 GitHub Issues 결과 수집 스크립트
Order Sheet를 정확히 해석하여 A/B 매핑을 올바르게 처리

사용법:
python collect_simple_fixed.py --token YOUR_TOKEN
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

def load_order_sheets():
    """모든 order sheet 로드"""
    order_sheets = {}
    base_path = "../user_study_comparisons"  # 상대 경로 수정
    
    # 실제 존재하는 comparison 폴더들
    comparison_folders = [
        "deepsink_vs_self_forcing",
        "deepsink_vs_long_live",
        "deepsink_vs_causvid",
        "deepsink_vs_rolling_forcing"
    ]
    
    for folder in comparison_folders:
        order_file = f"{base_path}/{folder}/order_sheet.txt"
        if os.path.exists(order_file):
            order_sheets[folder] = parse_order_sheet(order_file)
            print(f"✅ Loaded order sheet: {folder}")
        else:
            print(f"⚠️ Missing order sheet: {order_file}")
    
    return order_sheets

def parse_order_sheet(file_path):
    """Order sheet 파싱"""
    order_mapping = {}
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # 파일명 매핑 찾기
    in_mapping_section = False
    for line in lines:
        line = line.strip()
        
        if "Randomized Order" in line:
            in_mapping_section = True
            continue
            
        if in_mapping_section and ":" in line and "Model A" in line:
            # 예: "sampled_053.mp4: Model A = matrix, Model B = cogvideox_5b"
            parts = line.split(":")
            if len(parts) >= 2:
                filename = parts[0].strip()
                mapping_part = parts[1].strip()
                
                # Model A와 Model B 추출
                if "Model A = " in mapping_part and "Model B = " in mapping_part:
                    model_a_start = mapping_part.find("Model A = ") + 10
                    model_b_start = mapping_part.find("Model B = ") + 10
                    
                    model_a_end = mapping_part.find(",", model_a_start)
                    if model_a_end == -1:
                        model_a_end = mapping_part.find(" Model B", model_a_start)
                    
                    model_a = mapping_part[model_a_start:model_a_end].strip()
                    model_b = mapping_part[model_b_start:].strip()
                    
                    # _comparison.mp4 버전도 함께 저장
                    base_filename = filename.replace('.mp4', '')
                    comparison_filename = f"{base_filename}_comparison.mp4"
                    
                    order_mapping[filename] = {'model_a': model_a, 'model_b': model_b}
                    order_mapping[comparison_filename] = {'model_a': model_a, 'model_b': model_b}
    
    return order_mapping

def decode_choice(comparison_name, video_filename, choice, order_sheets):
    """A/B 선택을 실제 모델명으로 디코딩"""
    if comparison_name not in order_sheets:
        print(f"⚠️ Order sheet not found for: {comparison_name}")
        return None, None
    
    order_mapping = order_sheets[comparison_name]
    
    # 여러 가능한 파일명 형태 시도
    possible_keys = [
        video_filename,
        video_filename.replace('_comparison.mp4', '.mp4'),
        video_filename.replace('.mp4', '') + '.mp4',
        video_filename.replace('_comparison', '')
    ]
    
    mapping = None
    for key in possible_keys:
        if key in order_mapping:
            mapping = order_mapping[key]
            break
    
    if not mapping:
        print(f"⚠️ No mapping found for video: {video_filename} in {comparison_name}")
        return None, None
    
    if choice == 'A':
        return mapping['model_a'], mapping['model_b']
    elif choice == 'B':
        return mapping['model_b'], mapping['model_a']
    else:
        return None, None

def collect_issues(token, owner='paulcho98', repo='DeepSink_user_study'):
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

def analyze_results_with_order_sheets(results, order_sheets):
    """Order sheet를 사용한 정확한 결과 분석"""
    print("\n📊 정확한 분석 결과 (Order Sheet 기반):")
    print(f"총 참가자: {len(results)}")
    
    if not results:
        return
    
    question_names = [
        'color_consistency',
        'dynamic_motion', 
        'subject_consistency',
        'overall_quality'
    ]
    
    question_labels = {
        'color_consistency': '색상 일관성',
        'dynamic_motion': '동적 움직임', 
        'subject_consistency': '주체 일관성',
        'overall_quality': '전반적 품질'
    }
    
    for question_name in question_names:
        print(f"\n🏆 {question_labels[question_name]} ({question_name}):")
        model_wins = defaultdict(int)
        model_total = defaultdict(int)
        decode_errors = 0
        
        for result in results:
            responses = result.get('responses', {})
            for comparison_set, videos in responses.items():
                for video_file, response_data in videos.items():
                    choice = None
                    
                    # Handle different response formats
                    if isinstance(response_data, dict) and 'answers' in response_data:
                        choice = response_data['answers'].get(question_name)
                    elif isinstance(response_data, str):
                        if question_name == 'overall_quality':
                            choice = response_data
                    elif isinstance(response_data, dict) and 'choice' in response_data:
                        if question_name == 'overall_quality':
                            choice = response_data.get('choice')
                    
                    if choice in ['A', 'B']:
                        # 실제 order sheet를 사용하여 디코딩
                        chosen_model, other_model = decode_choice(
                            comparison_set, video_file, choice, order_sheets
                        )
                        
                        if chosen_model and other_model:
                            model_wins[chosen_model] += 1
                            model_total[chosen_model] += 1
                            model_total[other_model] += 1
                        else:
                            decode_errors += 1
        
        # Print results for this question
        print(f"  디코딩 오류: {decode_errors}개")
        for model in sorted(model_total.keys()):
            if model_total[model] > 0:
                win_rate = model_wins[model] / model_total[model]
                print(f"  {model}: {win_rate:.3f} ({model_wins[model]}/{model_total[model]})")
        
        if not model_total:
            print("  데이터 없음")

def main():
    parser = argparse.ArgumentParser(description='Collect GitHub Issues user study results with proper order sheet decoding')
    parser.add_argument('--token', default='None', help='GitHub Personal Access Token')
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
        print("2. python collect_simple_fixed.py --token YOUR_TOKEN")
        return
    
    # Load order sheets first
    print("📋 Loading order sheets...")
    order_sheets = load_order_sheets()
    
    if not order_sheets:
        print("❌ Order sheet를 로드할 수 없습니다.")
        return
    
    # Collect and analyze
    results = collect_issues(token)
    
    if results:
        # 날짜별 출력 디렉토리 생성
        current_date = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H%M%S")
        
        base_output_dir = "analysis_output"
        date_output_dir = os.path.join(base_output_dir, current_date)
        output_dir = os.path.join(date_output_dir, f"collection_{timestamp}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Save results
        filename = os.path.join(output_dir, "collected_results.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 결과 저장됨: {filename}")
        print(f"📁 출력 디렉토리: {output_dir}")
        
        # 분석 결과도 저장
        analysis_file = os.path.join(output_dir, "analysis_report.txt")
        with open(analysis_file, 'w', encoding='utf-8') as f:
            f.write(f"📊 사용자 연구 데이터 수집 분석 리포트\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"📅 수집 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"📋 참가자 수: {len(results)}명\n")
            f.write(f"📁 저장 위치: {filename}\n\n")
        
        print(f"📄 분석 리포트 저장됨: {analysis_file}")
        
        # 올바른 분석 (Order Sheet 기반)
        print("\n" + "="*50)
        print("분석 결과 (Order Sheet 기반):")
        analyze_results_with_order_sheets(results, order_sheets)
        
        # 기존 분석은 주석 처리 (필요시 주석 해제하여 비교 가능)
        # print("\n" + "="*50)
        # print("기존 방식 분석 (비교용 - 잘못된 결과):")
        # analyze_results_old_way(results)
        
    else:
        print("❌ 수집된 결과가 없습니다.")

def analyze_results_old_way(results):
    """기존 잘못된 방식으로 분석 (비교용)"""
    print("📊 기존 분석 결과 (잘못됨):")
    
    question_names = ['color_consistency', 'dynamic_motion', 'subject_consistency', 'overall_quality']
    
    for question_name in question_names:
        print(f"\n🏆 {question_name}:")
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
                    
                    if isinstance(response_data, dict) and 'answers' in response_data:
                        choice = response_data['answers'].get(question_name)
                    elif isinstance(response_data, str):
                        if question_name == 'overall_quality':
                            choice = response_data
                    
                    if choice in ['A', 'B']:
                        chosen = models[0] if choice == 'A' else models[1]
                        other = models[1] if choice == 'A' else models[0]
                        
                        model_wins[chosen] += 1
                        model_total[chosen] += 1
                        model_total[other] += 1
        
        for model in sorted(model_total.keys()):
            if model_total[model] > 0:
                win_rate = model_wins[model] / model_total[model]
                print(f"  {model}: {win_rate:.3f} ({model_wins[model]}/{model_total[model]})")

if __name__ == "__main__":
    main()