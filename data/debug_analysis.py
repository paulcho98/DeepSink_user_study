#!/usr/bin/env python3
"""
사용자 연구 결과 간단 분석 스크립트
"""

import json
import os
from collections import defaultdict

def parse_order_sheet(order_file):
    """Order sheet 파일 파싱"""
    order_mapping = {}
    try:
        with open(order_file, 'r') as f:
            for line in f:
                line = line.strip()
                if ':' in line and 'Model A' in line and 'Model B' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        filename = parts[0].strip()
                        rest = parts[1].strip()
                        
                        if 'Model A' in rest and 'Model B' in rest:
                            model_parts = rest.split(',')
                            model_a = None
                            model_b = None
                            
                            for part in model_parts:
                                part = part.strip()
                                if 'Model A' in part:
                                    model_a = part.split('=')[1].strip()
                                elif 'Model B' in part:
                                    model_b = part.split('=')[1].strip()
                            
                            if model_a and model_b:
                                order_mapping[filename + '_comparison.mp4'] = {
                                    'A': model_a,
                                    'B': model_b
                                }
    except Exception as e:
        print(f"⚠️ Error parsing order sheet {order_file}: {e}")
    return order_mapping

def analyze_simple():
    # 결과 로드
    result_files = [f for f in os.listdir('.') if f.startswith('collected_results_fixed_') and f.endswith('.json')]
    latest_file = sorted(result_files)[-1]
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"📊 참가자 수: {len(results)}")
    
    # Order sheet 하나 테스트
    order_file = "../user_study_comparisons/matrix_vs_cogvideox_5b/order_sheet.txt"
    if os.path.exists(order_file):
        order_mapping = parse_order_sheet(order_file)
        print(f"📋 Order mapping 예시: {order_mapping}")
    
    # 첫 번째 참가자 데이터 분석
    if results:
        first_participant = results[0]
        print(f"👤 첫 번째 참가자 ID: {first_participant.get('participantId', 'Unknown')}")
        
        responses = first_participant.get('responses', {})
        print(f"📝 응답한 비교 세트 수: {len(responses)}")
        
        for comparison_set, videos in responses.items():
            print(f"\n🎬 {comparison_set}:")
            print(f"   비디오 수: {len(videos)}")
            
            # 첫 번째 비디오 분석
            if videos:
                first_video = list(videos.keys())[0]
                first_response = videos[first_video]
                print(f"   첫 번째 비디오: {first_video}")
                
                if 'answers' in first_response:
                    answers = first_response['answers']
                    print(f"   답변: {answers}")
                    
                    # Order mapping과 결합
                    if os.path.exists(f"../user_study_comparisons/{comparison_set}/order_sheet.txt"):
                        order_mapping = parse_order_sheet(f"../user_study_comparisons/{comparison_set}/order_sheet.txt")
                        
                        if first_video in order_mapping:
                            mapping = order_mapping[first_video]
                            print(f"   Order mapping: {mapping}")
                            
                            for question, choice in answers.items():
                                chosen_model = mapping.get(choice, f"Unknown-{choice}")
                                print(f"   {question}: {choice} → {chosen_model}")

if __name__ == "__main__":
    analyze_simple()