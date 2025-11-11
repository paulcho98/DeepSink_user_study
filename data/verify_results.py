#!/usr/bin/env python3
"""
결과 검증 스크립트 - 수동으로 몇 개 케이스를 확인해봅시다
"""

import json

def verify_specific_cases():
    """구체적인 케이스들을 수동으로 검증"""
    
    # 결과 파일 로드
    with open('collected_results_fixed_20250922_144811.json', 'r') as f:
        results = json.load(f)
    
    print("🔍 수동 검증 - 구체적인 케이스들")
    print("="*60)
    
    # Case 1: matrix_vs_cogvideox_5b / sampled_053
    print("\n📋 Case 1: matrix_vs_cogvideox_5b / sampled_053")
    print("Order Sheet: sampled_053.mp4: Model A = matrix, Model B = cogvideox_5b")
    
    case1 = results[0]['responses']['matrix_vs_cogvideox_5b']['sampled_053_comparison.mp4']['answers']
    print("사용자 응답:")
    for question, choice in case1.items():
        if choice == 'A':
            selected_model = 'matrix'
        elif choice == 'B':
            selected_model = 'cogvideox_5b'
        else:
            selected_model = 'unknown'
        print(f"  {question}: {choice} → {selected_model}")
    
    # Case 2: matrix_vs_opensora / easy_v2_004
    print("\n📋 Case 2: matrix_vs_opensora / easy_v2_004")
    print("Order Sheet: easy_v2_004.mp4: Model A = opensora, Model B = matrix")
    
    case2 = results[0]['responses']['matrix_vs_opensora']['easy_v2_004_comparison.mp4']['answers']
    print("사용자 응답:")
    for question, choice in case2.items():
        if choice == 'A':
            selected_model = 'opensora'  # A가 opensora
        elif choice == 'B':
            selected_model = 'matrix'    # B가 matrix
        else:
            selected_model = 'unknown'
        print(f"  {question}: {choice} → {selected_model}")
    
    # 기존 방식과 비교
    print("\n" + "="*60)
    print("🚨 기존 잘못된 방식이라면:")
    print("matrix_vs_opensora에서 A=matrix, B=opensora로 잘못 가정")
    print("→ easy_v2_004에서 A 선택 시 matrix로 잘못 카운트")
    print("→ 실제로는 A=opensora이므로 opensora가 선택된 것!")
    
    print("\n✅ 올바른 방식:")
    print("Order sheet를 정확히 읽어서 A=opensora, B=matrix")
    print("→ A 선택 시 opensora로 정확히 카운트")

if __name__ == "__main__":
    verify_specific_cases()