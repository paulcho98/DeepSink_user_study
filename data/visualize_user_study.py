#!/usr/bin/env python3
"""
사용자 연구 결과 시각화 스크립트
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from collections import defaultdict
import os
from datetime import datetime

# 한글 폰트 설정
plt.rcParams['font.family'] = ['Arial Unicode MS', 'DejaVu Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def load_latest_results():
    """가장 최신 결과 파일 로드"""
    result_files = [f for f in os.listdir('.') if f.startswith('collected_results_fixed_') and f.endswith('.json')]
    if not result_files:
        raise FileNotFoundError("결과 파일을 찾을 수 없습니다.")
    
    # 가장 최신 파일 선택
    latest_file = sorted(result_files)[-1]
    print(f"📊 로딩 중: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f), latest_file

def parse_order_sheet(order_file):
    """Order sheet 파일 파싱"""
    order_mapping = {}
    try:
        with open(order_file, 'r') as f:
            for line in f:
                line = line.strip()
                if ':' in line and 'Model A' in line and 'Model B' in line:
                    # easy_v2_017.mp4: Model A = cogvideox_5b, Model B = matrix 형식 파싱
                    parts = line.split(':')
                    if len(parts) >= 2:
                        filename = parts[0].strip()
                        rest = parts[1].strip()
                        
                        # Model A와 Model B 추출
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
                                # .mp4를 _comparison.mp4로 교체
                                comparison_filename = filename.replace('.mp4', '_comparison.mp4')
                                order_mapping[comparison_filename] = {
                                    'A': model_a,
                                    'B': model_b
                                }
    except FileNotFoundError:
        print(f"⚠️ Order sheet not found: {order_file}")
    except Exception as e:
        print(f"⚠️ Error parsing order sheet {order_file}: {e}")
    return order_mapping

def load_order_sheets():
    """모든 order sheet 로드"""
    order_sheets = {}
    base_path = "../user_study_comparisons"
    
    comparison_folders = [
        "matrix_vs_cogvideox_5b", "matrix_vs_opensora", "matrix_vs_tavid", "matrix_vs_wan14b",
        "cogvideox_5b_vs_opensora", "cogvideox_5b_vs_tavid", "cogvideox_5b_vs_wan14b",
        "opensora_vs_tavid", "opensora_vs_wan14b", "tavid_vs_wan14b"
    ]
    
    for folder in comparison_folders:
        order_file = f"{base_path}/{folder}/order_sheet.txt"
        if os.path.exists(order_file):
            order_sheets[folder] = parse_order_sheet(order_file)
    
    return order_sheets

def analyze_results(results, order_sheets):
    """결과 분석"""
    questions = ['interaction_accuracy', 'entity_accuracy', 'temporal_consistency', 
                'prompt_faithfulness', 'overall_quality']
    
    question_names = {
        'interaction_accuracy': '상호작용 정확성',
        'entity_accuracy': '객체 반영 정확도', 
        'temporal_consistency': '시간적 일관성',
        'prompt_faithfulness': '프롬프트 충실도',
        'overall_quality': '전반적 품질'
    }
    
    model_wins = {q: defaultdict(int) for q in questions}
    model_total = {q: defaultdict(int) for q in questions}
    
    total_participants = len(results)
    print(f"📈 분석 중: {total_participants}명의 참가자 데이터")
    
    for participant in results:
        responses = participant['responses']
        
        for comparison_set, videos in responses.items():
            if comparison_set not in order_sheets:
                continue
                
            order_mapping = order_sheets[comparison_set]
            
            for video_file, response_data in videos.items():
                if video_file not in order_mapping:
                    continue
                    
                mapping = order_mapping[video_file]
                
                for question in questions:
                    if 'answers' in response_data and question in response_data['answers']:
                        choice = response_data['answers'][question]
                        chosen_model = mapping[choice]
                        other_model = mapping['B'] if choice == 'A' else mapping['A']
                        
                        model_wins[question][chosen_model] += 1
                        model_total[question][chosen_model] += 1
                        model_total[question][other_model] += 1
    
    return model_wins, model_total, question_names

def create_win_rate_chart(model_wins, model_total, question_names):
    """승률 차트 생성"""
    models = ['matrix', 'cogvideox_5b', 'opensora', 'tavid', 'wan14b']
    questions = list(question_names.keys())
    
    # 데이터 준비
    win_rates = []
    for model in models:
        model_rates = []
        for question in questions:
            if model_total[question][model] > 0:
                rate = model_wins[question][model] / model_total[question][model]
            else:
                rate = 0
            model_rates.append(rate * 100)  # 퍼센트로 변환
        win_rates.append(model_rates)
    
    # 히트맵 생성
    plt.figure(figsize=(12, 8))
    win_rates_df = pd.DataFrame(win_rates, 
                               index=models, 
                               columns=[question_names[q] for q in questions])
    
    sns.heatmap(win_rates_df, annot=True, fmt='.1f', cmap='RdYlBu_r', 
                cbar_kws={'label': '승률 (%)'}, vmin=0, vmax=100)
    
    plt.title('모델별 평가 항목 승률 (User Study Results)', fontsize=16, pad=20)
    plt.xlabel('평가 항목', fontsize=12)
    plt.ylabel('모델', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    return plt.gcf(), win_rates_df

def create_overall_ranking_chart(model_wins, model_total):
    """전반적 품질 기준 순위 차트"""
    question = 'overall_quality'
    models_data = []
    
    for model in model_total[question]:
        if model_total[question][model] > 0:
            win_rate = model_wins[question][model] / model_total[question][model]
            total_comparisons = model_total[question][model]
            wins = model_wins[question][model]
            models_data.append([model, win_rate * 100, wins, total_comparisons])
    
    if not models_data:
        # 데이터가 없으면 빈 차트 반환
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('전반적 품질 기준 모델 순위 - 데이터 없음')
        return plt.gcf(), pd.DataFrame()
    
    # 승률로 정렬
    models_data.sort(key=lambda x: x[1])  # 승률로 정렬
    
    models = [data[0] for data in models_data]
    win_rates = [data[1] for data in models_data]
    wins = [data[2] for data in models_data]
    totals = [data[3] for data in models_data]
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(models, win_rates, 
                    color=['#ff7f0e', '#2ca02c', '#d62728', '#1f77b4', '#9467bd'][:len(models)])
    
    # 바 위에 숫자 표시
    for i, bar in enumerate(bars):
        plt.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                f"{win_rates[i]:.1f}% ({wins[i]}/{totals[i]})",
                va='center', fontsize=10)
    
    plt.title('전반적 품질 기준 모델 순위', fontsize=16, pad=20)
    plt.xlabel('승률 (%)', fontsize=12)
    plt.ylabel('모델', fontsize=12)
    plt.xlim(0, max(win_rates) * 1.2 if win_rates else 100)
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    
    # DataFrame 생성 (CSV 저장용)
    models_df = pd.DataFrame({
        'Model': models,
        'WinRate': win_rates,
        'Wins': wins,
        'Total': totals
    })
    
    return plt.gcf(), models_df

def create_comparison_matrix(model_wins, model_total):
    """모델 간 직접 비교 매트릭스"""
    models = ['matrix', 'cogvideox_5b', 'opensora', 'tavid', 'wan14b']
    comparison_data = np.zeros((len(models), len(models)))
    
    # 모델 간 승률 계산 (전반적 품질 기준)
    question = 'overall_quality'
    
    for i, model1 in enumerate(models):
        for j, model2 in enumerate(models):
            if i == j:
                comparison_data[i][j] = 50  # 자기 자신과는 50%
            elif model_total[question][model1] > 0 and model_total[question][model2] > 0:
                # 간접적 비교 (승률 차이 기준)
                rate1 = model_wins[question][model1] / model_total[question][model1]
                rate2 = model_wins[question][model2] / model_total[question][model2]
                if rate1 + rate2 > 0:
                    comparison_data[i][j] = (rate1 / (rate1 + rate2)) * 100
                else:
                    comparison_data[i][j] = 50
            else:
                comparison_data[i][j] = 50
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(comparison_data, annot=True, fmt='.1f', 
                xticklabels=models, yticklabels=models,
                cmap='RdYlBu_r', vmin=0, vmax=100,
                cbar_kws={'label': '상대 승률 (%)'})
    
    plt.title('모델 간 상대적 성능 비교 매트릭스', fontsize=16, pad=20)
    plt.xlabel('상대방 모델', fontsize=12)
    plt.ylabel('기준 모델', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    return plt.gcf()

def create_detailed_stats_chart(model_wins, model_total, question_names):
    """상세 통계 차트"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    
    questions = list(question_names.keys())
    
    for i, question in enumerate(questions):
        ax = axes[i]
        
        models_data = []
        for model in model_total[question]:
            if model_total[question][model] > 0:
                win_rate = model_wins[question][model] / model_total[question][model]
                models_data.append([model, win_rate * 100, model_wins[question][model]])
        
        if models_data:
            # 승률로 내림차순 정렬
            models_data.sort(key=lambda x: x[1], reverse=True)
            
            models = [data[0] for data in models_data]
            win_rates = [data[1] for data in models_data]
            counts = [data[2] for data in models_data]
            
            bars = ax.bar(models, win_rates, 
                         color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'][:len(models)])
            
            # 바 위에 값 표시
            for j, bar in enumerate(bars):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{height:.1f}%\n({counts[j]})',
                       ha='center', va='bottom', fontsize=9)
            
            ax.set_title(question_names[question], fontsize=14, pad=10)
            ax.set_ylabel('승률 (%)', fontsize=10)
            max_rate = max(win_rates) if win_rates else 0
            ax.set_ylim(0, max_rate * 1.3 if max_rate > 0 else 100)
            ax.tick_params(axis='x', rotation=45)
            ax.grid(axis='y', alpha=0.3)
        else:
            # 데이터가 없는 경우
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(question_names[question], fontsize=14, pad=10)
    
    # 빈 서브플롯 숨기기
    if len(questions) < len(axes):
        axes[-1].set_visible(False)
    
    plt.suptitle('평가 항목별 모델 성능 상세 분석', fontsize=16, y=0.95)
    plt.tight_layout()
    
    return fig

def create_radar_chart(model_wins, model_total, question_names):
    """모델별 5개 평가 지표에 대한 Radar Chart 생성"""
    # 전체 모델 목록 수집
    all_models = set()
    for question_data in model_total.values():
        all_models.update(question_data.keys())
    all_models = sorted(list(all_models))
    
    # 모델별 승률 계산
    model_scores = {}
    for model in all_models:
        scores = []
        for question in question_names.keys():
            if model in model_total[question] and model_total[question][model] > 0:
                win_rate = model_wins[question][model] / model_total[question][model]
            else:
                win_rate = 0
            scores.append(win_rate)
        model_scores[model] = scores
    
    # 평가 지표 이름 (한국어)
    categories = [
        '상호작용\n정확성',
        '객체 반영\n정확도', 
        '시간적\n일관성',
        '의미적\n정렬',
        '전반적\n품질'
    ]
    
    # 각도 계산
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # 닫힌 폴리곤을 위해
    
    # 컬러 팔레트
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', 
              '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43']
    
    # 서브플롯 생성 (2x3 그리드)
    fig, axes = plt.subplots(2, 3, figsize=(18, 12), subplot_kw=dict(projection='polar'))
    fig.suptitle('🎯 모델별 평가 지표 Radar Chart', fontsize=20, fontweight='bold', y=0.98)
    
    # 축을 1차원으로 평탄화
    axes_flat = axes.flatten()
    
    # 각 모델별로 radar chart 생성
    for idx, model in enumerate(all_models[:6]):  # 최대 6개 모델
        if idx >= len(axes_flat):
            break
            
        ax = axes_flat[idx]
        scores = model_scores[model]
        scores += scores[:1]  # 닫힌 폴리곤을 위해
        
        # Radar chart 그리기
        color = colors[idx % len(colors)]
        ax.plot(angles, scores, 'o-', linewidth=2, label=model, color=color)
        ax.fill(angles, scores, alpha=0.25, color=color)
        
        # 축 설정
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=8)
        ax.grid(True)
        
        # 제목 설정
        ax.set_title(f'{model}', fontsize=14, fontweight='bold', pad=20)
        
        # 승률 값을 텍스트로 표시
        for angle, score, category in zip(angles[:-1], scores[:-1], categories):
            ax.text(angle, score + 0.05, f'{score:.1%}', 
                   horizontalalignment='center', fontsize=8, fontweight='bold')
    
    # 남은 서브플롯 숨기기
    for idx in range(len(all_models), len(axes_flat)):
        axes_flat[idx].set_visible(False)
    
    plt.tight_layout()
    return fig

def create_combined_radar_chart(model_wins, model_total, question_names):
    """모든 모델을 한 Radar Chart에 표시"""
    # 전체 모델 목록 수집
    all_models = set()
    for question_data in model_total.values():
        all_models.update(question_data.keys())
    all_models = sorted(list(all_models))
    
    # 모델별 승률 계산
    model_scores = {}
    for model in all_models:
        scores = []
        for question in question_names.keys():
            if model in model_total[question] and model_total[question][model] > 0:
                win_rate = model_wins[question][model] / model_total[question][model]
            else:
                win_rate = 0
            scores.append(win_rate)
        model_scores[model] = scores
    
    # 평가 지표 이름 (한국어)
    categories = [
        '상호작용 정확성',
        '객체 반영 정확도', 
        '시간적 일관성',
        '의미적 정렬',
        '전반적 품질'
    ]
    
    # 각도 계산
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # 닫힌 폴리곤을 위해
    
    # 컬러 팔레트
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57']
    
    # Figure 생성
    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw=dict(projection='polar'))
    fig.suptitle('🎯 모든 모델 비교 Radar Chart', fontsize=18, fontweight='bold', y=0.95)
    
    # 각 모델별로 radar chart 그리기
    for idx, model in enumerate(all_models):
        scores = model_scores[model]
        scores += scores[:1]  # 닫힌 폴리곤을 위해
        
        color = colors[idx % len(colors)]
        ax.plot(angles, scores, 'o-', linewidth=2, label=model, color=color, markersize=6)
        ax.fill(angles, scores, alpha=0.15, color=color)
    
    # 축 설정
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=12)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], fontsize=10)
    ax.grid(True)
    
    # 범례 설정
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=12)
    
    plt.tight_layout()
    return fig

def save_visualizations(filename_prefix):
    """모든 시각화 저장"""
    try:
        # 결과 로드
        results, filename = load_latest_results()
        order_sheets = load_order_sheets()
        
        print(f"📊 Order sheets 로드됨: {len(order_sheets)}개")
        
        # 분석 수행
        model_wins, model_total, question_names = analyze_results(results, order_sheets)
        
        # 날짜별 출력 디렉토리 생성
        current_date = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H%M%S")
        
        base_output_dir = "visualization_output"
        date_output_dir = os.path.join(base_output_dir, current_date)
        output_dir = os.path.join(date_output_dir, f"analysis_{timestamp}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"📁 출력 디렉토리: {output_dir}")
        print(f"📊 분석 중: {len(results)}명의 참가자 데이터")
        
        # 1. 히트맵 (승률)
        print("📈 히트맵 생성 중...")
        fig1, win_rates_df = create_win_rate_chart(model_wins, model_total, question_names)
        fig1.savefig(f"{output_dir}/win_rates_heatmap.png", dpi=300, bbox_inches='tight')
        win_rates_df.to_csv(f"{output_dir}/win_rates_data.csv")
        plt.close(fig1)
        
        # 2. 전반적 순위
        print("🏆 순위 차트 생성 중...")
        fig2, ranking_df = create_overall_ranking_chart(model_wins, model_total)
        fig2.savefig(f"{output_dir}/overall_ranking.png", dpi=300, bbox_inches='tight')
        ranking_df.to_csv(f"{output_dir}/ranking_data.csv")
        plt.close(fig2)
        
        # 3. 비교 매트릭스
        print("🔄 비교 매트릭스 생성 중...")
        fig3 = create_comparison_matrix(model_wins, model_total)
        fig3.savefig(f"{output_dir}/comparison_matrix.png", dpi=300, bbox_inches='tight')
        plt.close(fig3)
        
        # 4. 상세 통계
        print("📊 상세 통계 생성 중...")
        fig4 = create_detailed_stats_chart(model_wins, model_total, question_names)
        fig4.savefig(f"{output_dir}/detailed_stats.png", dpi=300, bbox_inches='tight')
        plt.close(fig4)
        
        # 5. 개별 모델 Radar Charts
        print("🎯 개별 모델 Radar Chart 생성 중...")
        fig5 = create_radar_chart(model_wins, model_total, question_names)
        fig5.savefig(f"{output_dir}/individual_radar_charts.png", dpi=300, bbox_inches='tight')
        plt.close(fig5)
        
        # 6. 통합 Radar Chart
        print("🎯 통합 Radar Chart 생성 중...")
        fig6 = create_combined_radar_chart(model_wins, model_total, question_names)
        fig6.savefig(f"{output_dir}/combined_radar_chart.png", dpi=300, bbox_inches='tight')
        plt.close(fig6)
        
        # 요약 리포트 생성
        print("📄 요약 리포트 생성 중...")
        create_summary_report(model_wins, model_total, question_names, 
                            f"{output_dir}/summary_report.txt", 
                            filename, len(results))
        
        # 분석 메타데이터 생성
        print("📋 분석 메타데이터 생성 중...")
        create_analysis_metadata(output_dir, filename, len(results), timestamp)
        
        print(f"\n✅ 모든 시각화 완료!")
        print(f"📁 출력 디렉토리: {output_dir}/")
        print(f"📅 날짜: {current_date}")
        print(f"🕐 시간: {timestamp}")
        
        return output_dir, current_date, timestamp
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        raise

def create_summary_report(model_wins, model_total, question_names, output_file, data_file, participant_count):
    """요약 리포트 생성"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("사용자 연구 결과 요약 리포트\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"데이터 파일: {data_file}\n")
        f.write(f"참가자 수: {participant_count}명\n")
        f.write(f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 전반적 품질 순위
        f.write("🏆 전반적 품질 순위\n")
        f.write("-" * 30 + "\n")
        
        question = 'overall_quality'
        models_data = []
        for model in model_total[question]:
            if model_total[question][model] > 0:
                win_rate = model_wins[question][model] / model_total[question][model]
                models_data.append((model, win_rate * 100, model_wins[question][model], model_total[question][model]))
        
        models_data.sort(key=lambda x: x[1], reverse=True)
        
        for i, (model, rate, wins, total) in enumerate(models_data, 1):
            f.write(f"{i}. {model}: {rate:.1f}% ({wins}/{total})\n")
        
        f.write("\n")
        
        # 평가 항목별 최고 성능 모델
        f.write("📊 평가 항목별 최고 성능 모델\n")
        f.write("-" * 40 + "\n")
        
        for question, korean_name in question_names.items():
            best_model = None
            best_rate = 0
            
            for model in model_total[question]:
                if model_total[question][model] > 0:
                    rate = model_wins[question][model] / model_total[question][model]
                    if rate > best_rate:
                        best_rate = rate
                        best_model = model
            
            if best_model:
                f.write(f"{korean_name}: {best_model} ({best_rate*100:.1f}%)\n")
        
        f.write("\n")
        
        # 상세 통계
        f.write("📈 상세 통계\n")
        f.write("-" * 20 + "\n")
        
        for question, korean_name in question_names.items():
            f.write(f"\n{korean_name}:\n")
            models_data = []
            for model in model_total[question]:
                if model_total[question][model] > 0:
                    win_rate = model_wins[question][model] / model_total[question][model]
                    models_data.append((model, win_rate * 100, model_wins[question][model], model_total[question][model]))
            
            models_data.sort(key=lambda x: x[1], reverse=True)
            
            for model, rate, wins, total in models_data:
                f.write(f"  {model}: {rate:.1f}% ({wins}/{total})\n")

def create_analysis_metadata(output_dir, source_filename, participant_count, timestamp):
    """분석 메타데이터 파일 생성"""
    metadata_file = os.path.join(output_dir, "analysis_metadata.json")
    
    metadata = {
        "analysis_info": {
            "timestamp": f"{datetime.now().strftime('%Y-%m-%d')} {timestamp}",
            "date": datetime.now().strftime('%Y-%m-%d'),
            "time": timestamp,
            "source_file": source_filename,
            "participant_count": participant_count,
            "analysis_type": "user_study_visualization"
        },
        "generated_files": {
            "visualizations": [
                "win_rates_heatmap.png",
                "overall_ranking.png", 
                "comparison_matrix.png",
                "detailed_stats.png",
                "individual_radar_charts.png",
                "combined_radar_chart.png"
            ],
            "data_files": [
                "win_rates_data.csv",
                "ranking_data.csv"
            ],
            "reports": [
                "summary_report.txt",
                "analysis_metadata.json"
            ]
        },
        "folder_structure": {
            "description": "날짜별 폴더 구조로 분석 결과 저장",
            "pattern": "visualization_output/YYYY-MM-DD/analysis_HHMMSS/",
            "example": f"visualization_output/{datetime.now().strftime('%Y-%m-%d')}/analysis_{timestamp}/"
        }
    }
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # README 파일도 생성
    readme_file = os.path.join(output_dir, "README.md")
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(f"""# 🎨 사용자 연구 시각화 결과

## 📊 분석 정보
- **분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **데이터 소스**: {source_filename}
- **참가자 수**: {participant_count}명
- **분석 타임스탬프**: {timestamp}

## 📁 생성된 파일들

### 🖼️ 시각화 파일
1. **win_rates_heatmap.png** - 모델별 승률 히트맵
2. **overall_ranking.png** - 전반적 성능 순위
3. **comparison_matrix.png** - 모델 간 비교 매트릭스
4. **detailed_stats.png** - 상세 통계 차트
5. **individual_radar_charts.png** - 개별 모델 레이더 차트
6. **combined_radar_chart.png** - 통합 레이더 차트

### 📊 데이터 파일
1. **win_rates_data.csv** - 승률 원본 데이터
2. **ranking_data.csv** - 순위 원본 데이터

### 📄 리포트 파일
1. **summary_report.txt** - 종합 분석 리포트
2. **analysis_metadata.json** - 분석 메타데이터
3. **README.md** - 이 파일

## 🗂️ 폴더 구조
```
visualization_output/
└── {datetime.now().strftime('%Y-%m-%d')}/
    └── analysis_{timestamp}/
        ├── 시각화 파일들 (.png)
        ├── 데이터 파일들 (.csv)
        ├── 리포트 파일들 (.txt, .json)
        └── README.md
```

---
*생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
""")

if __name__ == "__main__":
    print("🎨 사용자 연구 시각화 시작...")
    try:
        output_dir, current_date, timestamp = save_visualizations("user_study")
        print(f"\n🎉 시각화 완료! 결과를 확인해보세요:")
        print(f"📁 {output_dir}/")
        print(f"📅 날짜: {current_date}")
        print(f"🕐 시간: {timestamp}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")