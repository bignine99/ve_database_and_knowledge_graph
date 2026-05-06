"""
조달청 설계VE 사례집 2025 추출기 (005)
======================================
- 2페이지/제안 (짝수: 제안 + LCC, 홀수: 성능/가치 평가)
- 공종별: 건축, 기계, 토목, 조경, 전기, 통신
- 한글 텍스트 정상 추출 가능
"""
import fitz, json, re, sys, io, os
import psycopg2, psycopg2.extras
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

PDF_PATH = BASE_DIR / ".raw_data" / "004_조달청 설계VE 사례집_2025.pdf"
OUT_DIR = BASE_DIR / "data" / "extracted_005"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ID = "pps_2025_ve"
PROJECT_NAME = "조달청 설계VE 사례집 2025"
SOURCE_YEAR = 2025
SOURCE_ORG = "조달청"


def get_pg():
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"),
        user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"),
        sslmode="require",
    )


def parse_num(s):
    if not s: return 0
    s = str(s).replace(',', '').replace(' ', '').replace('%', '').strip()
    m = re.search(r'-?[\d.]+', s)
    return float(m.group()) if m else 0


def detect_proposal_pages(doc):
    """제안 페이지 페어 감지 — '제 안 명' + '개 선 전' + '개 선 후'"""
    pairs = []
    total = len(doc)
    
    for i in range(total):
        text = doc[i].get_text()
        if '제 안 명' in text and '개 선 전' in text and '개 선 후' in text:
            pairs.append(i)
    
    return pairs


def extract_from_page1(text):
    """첫 페이지: 제안명, 공종, 개선전/후, LCC, 성능/가치점수"""
    lines = text.split('\n')
    d = {
        'proposal_title': '', 'field': '', 'target_function': '',
        'original_desc': '', 'alternative_desc': '',
        'lcc_original': 0, 'lcc_alternative': 0, 'lcc_savings': 0, 'lcc_savings_rate': 0,
        'perf_original': 500, 'perf_alternative': 0,
        'value_original': 500, 'value_alternative': 0, 'value_improvement': 0,
        'advantages': '', 'effect': '',
    }
    
    # 제안명
    for i, line in enumerate(lines):
        if '제 안 명' in line:
            if i + 1 < len(lines):
                d['proposal_title'] = lines[i + 1].strip()
            break
    
    # 공종
    for i, line in enumerate(lines):
        if line.strip() == '공종':
            if i + 1 < len(lines):
                d['field'] = lines[i + 1].strip()
            break
    
    # 대상기능
    for i, line in enumerate(lines):
        if '대상기능' in line:
            if i + 1 < len(lines):
                d['target_function'] = lines[i + 1].strip()
            break
    
    # 개선전/후 설명 — '개 선 전' ~ '개 선 후' 사이, 그리고 '개 선 후' 이후
    in_before = False
    in_after = False
    before_lines = []
    after_lines = []
    
    for i, line in enumerate(lines):
        ls = line.strip()
        if '개 선 전' in ls:
            in_before = True
            in_after = False
            continue
        if '개 선 후' in ls:
            in_before = False
            in_after = True
            continue
        if ls in ('경', '제', '성', '평', '가', '결', '과', '안', '내', '용'):
            continue
        if '생애주기비용' in ls or '가치향상효과' in ls:
            in_before = False
            in_after = False
            continue
        
        if in_before and ls and ls != 'Ÿ':
            before_lines.append(ls.replace('Ÿ', '').strip())
        elif in_after and ls and ls != 'Ÿ':
            after_lines.append(ls.replace('Ÿ', '').strip())
    
    d['original_desc'] = ' '.join(before_lines)[:300]
    d['alternative_desc'] = ' '.join(after_lines)[:300]
    
    # LCC 데이터 — 개선전/후 숫자 행
    nums = re.findall(r'[\d,]+', text)
    nums_clean = [n.replace(',', '') for n in nums if len(n.replace(',', '')) >= 3]
    
    # 성능점수, 가치점수 추출
    for i, line in enumerate(lines):
        ls = line.strip()
        if ls == '500':
            # 500은 원안 기본점수
            pass
        if ls.startswith('P1=') or ls.startswith('P2='):
            pass
    
    # 절감률 추출
    rate_m = re.search(r'(\d+)%', text[text.find('절감율'):] if '절감율' in text else '')
    if rate_m:
        d['lcc_savings_rate'] = parse_num(rate_m.group(1))
    
    # 가치향상도 추출
    vi_m = re.search(r'(\d+)%', text[text.find('가치향상효과'):] if '가치향상효과' in text else '')
    # 더 구체적 추출: L1, L2, P2, V2
    for i, line in enumerate(lines):
        ls = line.strip()
        if 'L1=' in ls and i + 1 < len(lines):
            d['lcc_original'] = parse_num(lines[i + 1].strip())
        if 'L2=' in ls:
            # L2= 와 같은 줄 또는 다음 줄
            if i + 1 < len(lines):
                next_val = lines[i + 1].strip()
                d['lcc_alternative'] = parse_num(next_val)
        if 'P2=' in ls and i + 1 < len(lines):
            # P2 다음 줄들에서 숫자
            pass
    
    # 장점
    for i, line in enumerate(lines):
        if '장   점' in line:
            for j in range(i + 1, min(i + 5, len(lines))):
                ls = lines[j].strip().replace('Ÿ', '').strip()
                if ls and ls != '-':
                    d['advantages'] = ls[:200]
                    break
            break
    
    # 효과
    for i, line in enumerate(lines):
        if '효   과' in line:
            for j in range(i + 1, min(i + 3, len(lines))):
                ls = lines[j].strip()
                if ls and ls != '-':
                    d['effect'] = ls[:200]
                    break
            break
    
    return d


def extract_from_page2(text):
    """둘째 페이지: 초기공사비, 성능평가 6항목, 가치평가"""
    lines = text.split('\n')
    d = {
        'cost_original': 0, 'cost_alternative': 0, 'cost_savings': 0,
        'perf_scores': [],
        'perf_original_total': 500, 'perf_alternative_total': 0, 'perf_improvement': 0,
        'lcc_original': 0, 'lcc_alternative': 0,
        'value_original': 500, 'value_alternative': 0, 'value_improvement': 0,
    }
    
    # 초기공사비 합계
    for i, line in enumerate(lines):
        if '합  계' in line.strip() or '합 계' in line.strip():
            # 다음 2줄에서 숫자 추출
            if i + 1 < len(lines):
                d['cost_original'] = parse_num(lines[i + 1].strip())
            if i + 2 < len(lines):
                d['cost_alternative'] = parse_num(lines[i + 2].strip())
            break
    
    # 절감액
    for i, line in enumerate(lines):
        if '절감액' in line.strip():
            for j in range(i + 1, min(i + 3, len(lines))):
                val = parse_num(lines[j].strip())
                if val > 0:
                    d['cost_savings'] = val
                    break
            break
    
    # 성능평가 — 6개 카테고리: 시공성, 유지관리성, 공간활용성, 독창성, 편의성, 안전성
    categories = ['시공성', '유지관리성', '공간활용성', '독창성', '편의성', '안전성']
    for cat in categories:
        for i, line in enumerate(lines):
            if cat in line.strip():
                # 같은 줄 또는 다음 4줄에서 숫자 5개: 가중치, 원안등급, 원안점수, 대안등급, 대안점수
                nums = []
                for j in range(i, min(i + 6, len(lines))):
                    for n in re.findall(r'\d+', lines[j]):
                        nums.append(int(n))
                if len(nums) >= 5:
                    d['perf_scores'].append({
                        'category': cat,
                        'weight': nums[0],
                        'original_grade': nums[1],
                        'original_score': nums[2],
                        'alternative_grade': nums[3],
                        'alternative_score': nums[4],
                    })
                break
    
    # 성능점수 합계
    for i, line in enumerate(lines):
        if '성능점수(P)' in line.strip() or '성능점수' in line.strip():
            nums = []
            for j in range(i, min(i + 3, len(lines))):
                for n in re.findall(r'[\d,]+', lines[j]):
                    val = parse_num(n)
                    if val >= 100:
                        nums.append(val)
            if len(nums) >= 2:
                d['perf_original_total'] = nums[0]
                d['perf_alternative_total'] = nums[1]
            elif len(nums) == 1:
                d['perf_alternative_total'] = nums[0]
            break
    
    # 성능향상율
    for i, line in enumerate(lines):
        if '성능향상율' in line.strip() or '성능향상률' in line.strip():
            m = re.search(r'([\d.]+)%', text[text.find('성능향상'):])
            if m:
                d['perf_improvement'] = parse_num(m.group(1))
            break
    
    # 가치점수
    for i, line in enumerate(lines):
        if '가치점수' in line.strip():
            nums = []
            for j in range(i, min(i + 3, len(lines))):
                for n in re.findall(r'[\d,]+', lines[j]):
                    val = parse_num(n)
                    if val >= 100:
                        nums.append(val)
            if len(nums) >= 2:
                d['value_original'] = nums[0]
                d['value_alternative'] = nums[1]
            break
    
    # 가치향상도
    m = re.search(r'가치향상도.*?([\d.]+)%', text, re.DOTALL)
    if m:
        d['value_improvement'] = parse_num(m.group(1))
    
    # LCC
    for i, line in enumerate(lines):
        if 'L C C' in line.strip() or 'LCC' in line.strip():
            nums = []
            for j in range(i, min(i + 3, len(lines))):
                for n in re.findall(r'[\d,]+', lines[j]):
                    val = parse_num(n)
                    if val >= 1000:
                        nums.append(val)
            if len(nums) >= 2:
                d['lcc_original'] = nums[0]
                d['lcc_alternative'] = nums[1]
            break
    
    return d


def map_field_category(field):
    mapping = {
        '건축': '건축공사', '기계': '기계설비공사', '토목': '토목공사',
        '조경': '조경공사', '전기': '전기공사', '통신': '통신공사',
        '소방': '소방공사',
    }
    return mapping.get(field, field)


def insert_to_supabase(all_data):
    pg = get_pg()
    cur = pg.cursor()
    
    cur.execute("""INSERT INTO projects (project_id, project_name, file_path, total_alternatives, source_file, source_year, source_org)
        VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (project_id) DO UPDATE SET total_alternatives = EXCLUDED.total_alternatives""",
        (PROJECT_ID, PROJECT_NAME, str(PDF_PATH), len(all_data), PDF_PATH.name, SOURCE_YEAR, SOURCE_ORG))
    
    cur.execute("SELECT COALESCE(MAX(alt_number), 0) FROM alternatives")
    max_num = cur.fetchone()[0]
    
    for i, d in enumerate(all_data):
        alt_num = max_num + i + 1
        alt_id = f"pps_{alt_num:03d}"
        
        # HOW1 매핑
        how1 = map_field_category(d['field'])
        
        cur.execute("""INSERT INTO alternatives (
                alt_id, project_id, alt_number, proposal_title,
                original_description, alternative_description,
                advantages, disadvantages, project_name, source_page,
                field_category, value_type_corrected, how2_code, how2_name, space
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (alt_id) DO NOTHING""",
            (alt_id, PROJECT_ID, alt_num, d['proposal_title'],
             d['original_desc'], d['alternative_desc'],
             d.get('advantages', ''), '', PROJECT_NAME, d['source_page'],
             d['field'], d.get('value_type', '가치혁신형'),
             d.get('how2_code', ''), d.get('how2_name', ''), d.get('space', '')))
        
        # 비용
        savings = d.get('cost_savings', 0)
        savings_rate = 0
        if d.get('cost_original', 0) > 0:
            savings_rate = round(savings / d['cost_original'] * 100, 2)
        
        cur.execute("""INSERT INTO cost_evaluations (alt_id, cost_type, original_cost, alternative_cost, savings_amount, savings_rate)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (alt_id, 'project_initial', d.get('cost_original', 0) / 1000000,  # 원→백만원
             d.get('cost_alternative', 0) / 1000000, savings / 1000000, savings_rate))
        
        # 가치
        cur.execute("""INSERT INTO value_evaluations (alt_id, performance_original, performance_alternative,
                performance_change_rate, cost_change_rate, value_change_rate)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (alt_id, d.get('perf_original_total', 500), d.get('perf_alternative_total', 0),
             d.get('perf_improvement', 0), savings_rate, d.get('value_improvement', 0)))
        
        # 성능 상세
        for ps in d.get('perf_scores', []):
            cur.execute("""INSERT INTO performance_scores (alt_id, category, original_score, alternative_score, score_delta)
                VALUES (%s,%s,%s,%s,%s)""",
                (alt_id, ps['category'], ps['original_score'], ps['alternative_score'],
                 ps['alternative_score'] - ps['original_score']))
    
    pg.commit()
    pg.close()
    return max_num + 1, max_num + len(all_data)


def run():
    print("=" * 60, flush=True)
    print("조달청 설계VE 사례집 2025 추출", flush=True)
    print("=" * 60, flush=True)
    
    doc = fitz.open(str(PDF_PATH))
    total = len(doc)
    print(f"  총 {total} 페이지", flush=True)
    
    # Phase 1: 제안 페이지 감지
    print(f"\n  Phase 1: 제안 페이지 감지...", flush=True)
    proposal_pages = detect_proposal_pages(doc)
    print(f"  제안 페이지: {len(proposal_pages)}건", flush=True)
    
    # Phase 2: CUBE 분류 로드
    sys.path.insert(0, str(BASE_DIR))
    from src.cube_taxonomy import classify_how2, classify_space
    
    # Phase 3: 추출
    print(f"\n  Phase 2: 데이터 추출...", flush=True)
    all_data = []
    
    for idx, pg_idx in enumerate(proposal_pages):
        text1 = doc[pg_idx].get_text()
        
        # 페이지1 추출
        d1 = extract_from_page1(text1)
        
        # 페이지2 (다음 페이지)
        d2 = {}
        if pg_idx + 1 < total:
            text2 = doc[pg_idx + 1].get_text()
            if '성능평가' in text2 or '가치평가' in text2:
                d2 = extract_from_page2(text2)
        
        # 병합
        d = {
            'source_page': pg_idx + 1,
            'proposal_title': d1['proposal_title'],
            'field': d1['field'],
            'target_function': d1['target_function'],
            'original_desc': d1['original_desc'],
            'alternative_desc': d1['alternative_desc'],
            'advantages': d1['advantages'],
            'effect': d1['effect'],
            'cost_original': d2.get('cost_original', 0),
            'cost_alternative': d2.get('cost_alternative', 0),
            'cost_savings': d2.get('cost_savings', 0),
            'perf_scores': d2.get('perf_scores', []),
            'perf_original_total': d2.get('perf_original_total', 500),
            'perf_alternative_total': d2.get('perf_alternative_total', 0),
            'perf_improvement': d2.get('perf_improvement', 0),
            'value_original': d2.get('value_original', 500),
            'value_alternative': d2.get('value_alternative', 0),
            'value_improvement': d2.get('value_improvement', 0),
            'value_type': '가치혁신형' if d2.get('value_improvement', 0) > 0 else '비용절감형',
        }
        
        # CUBE 분류
        title_text = d['proposal_title'] + ' ' + d['original_desc'] + ' ' + d['alternative_desc']
        how2_list = classify_how2(title_text)
        if how2_list:
            h = how2_list[0]
            d['how2_code'] = f"{h[0]}-{h[1]}" if len(h) >= 2 else ''
            d['how2_name'] = h[2] if len(h) >= 3 else ''
        else:
            d['how2_code'] = ''
            d['how2_name'] = ''
        
        space_list = classify_space(title_text)
        d['space'] = space_list[0] if isinstance(space_list, list) and space_list else ''
        
        # JSON 저장
        json_path = OUT_DIR / f"pps_{len(all_data)+1:03d}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2, default=str)
        
        all_data.append(d)
        
        if (idx + 1) % 20 == 0:
            print(f"  ... {idx+1}/{len(proposal_pages)} ({d['field']})", flush=True)
    
    print(f"\n  {len(all_data)}건 추출 완료", flush=True)
    
    # Supabase 적재
    print(f"\n  DB 적재 중...", flush=True)
    start, end = insert_to_supabase(all_data)
    print(f"  대안 #{start}~#{end} 적재 완료", flush=True)
    
    # 통계
    fields = {}
    for d in all_data:
        fields[d['field']] = fields.get(d['field'], 0) + 1
    
    perf_count = sum(1 for d in all_data if d.get('perf_scores'))
    cost_count = sum(1 for d in all_data if d.get('cost_savings', 0) > 0)
    
    doc.close()
    print(f"\n{'='*60}", flush=True)
    print(f"  총 추출: {len(all_data)}건", flush=True)
    print(f"  공종별: {fields}", flush=True)
    print(f"  성능평가 있음: {perf_count}건", flush=True)
    print(f"  비용절감 있음: {cost_count}건", flush=True)
    print(f"  대안: #{start} ~ #{end}", flush=True)


if __name__ == "__main__":
    run()
