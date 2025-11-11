#!/usr/bin/env python3
"""
전체 통계 수동 검증
"""

import json
from collections import defaultdict

def manual_count():
    """전체 통계를 수동으로 다시 계산"""
    
    # 결과 로드
    with open('../collected_results_fixed_20250922_144811.json', 'r') as f:
        results = json.load(f)
    
    # Order sheet 정보 (수동 입력으로 검증)
    order_mappings = {
        'matrix_vs_cogvideox_5b': {
            'sampled_053_comparison.mp4': {'A': 'matrix', 'B': 'cogvideox_5b'},
            'generated_038_comparison.mp4': {'A': 'matrix', 'B': 'cogvideox_5b'},
        },
        'matrix_vs_opensora': {
            'sampled_053_comparison.mp4': {'A': 'matrix', 'B': 'opensora'},
            'easy_v2_004_comparison.mp4': {'A': 'opensora', 'B': 'matrix'},
        }
        # 더 많지만 샘플만 확인
    }
    
    print("🔢 수동 카운팅 (샘플 데이터):")
    print("="*50)
    
    model_wins = defaultdict(int)
    model_total = defaultdict(int)
    
    # 첫 번째 참가자의 overall_quality만 확인
    participant = results[0]
    responses = participant['responses']
    
    for comparison_set, videos in responses.items():
        if comparison_set in order_mappings:
            print(f"\n📊 {comparison_set}:")
            for video_file, response_data in videos.items():
                if video_file in order_mappings[comparison_set]:
                    choice = response_data['answers']['overall_quality']
                    mapping = order_mappings[comparison_set][video_file]
                    
                    chosen_model = mapping[choice]
                    other_model = mapping['B'] if choice == 'A' else mapping['A']
                    
                    print(f"  {video_file}: 선택={choice} → {chosen_model}")
                    
                    model_wins[chosen_model] += 1
                    model_total[chosen_model] += 1
                    model_total[other_model] += 1
    
    print(f"\n🏆 Overall Quality 결과 (1명, 4개 비디오):")
    for model in sorted(model_total.keys()):
        if model_total[model] > 0:
            win_rate = model_wins[model] / model_total[model]
            print(f"  {model}: {win_rate:.3f} ({model_wins[model]}/{model_total[model]})")
    
    print(f"\n📈 예상 전체 결과 (3명×4개 = 12개 케이스에서):")
    print(f"matrix가 이런 패턴이라면:")
    print(f"  matrix: 3/4 = 0.75 승률")
    print(f"  opensora: 1/4 = 0.25 승률")

if __name__ == "__main__":
    manual_count()