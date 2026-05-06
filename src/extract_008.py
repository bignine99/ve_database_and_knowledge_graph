"""
왕산2초중통합 신축 — 대안구체화 추출기 (008)
=============================================
- 2페이지/제안: 홀수(대안개요+비용), 짝수(성능세부평가)
- 제안명: [대안-XX] 형식
- 성능평가: 7항목 상세 (시공성, 유지관리성, 공간활용성, 독창성, 편의성, 안전성, 환경/경관성)
"""
import fitz, json, re, sys, io, os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

PDF_PATH = BASE_DIR / ".raw_data" / "007_왕산2초중통합신축_대안구체화.pdf"
OUT_DIR = BASE_DIR / "data" / "extracted_008"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ID = "wangsan_school_2024"
PROJECT_NAME = "왕산2초중통합 신축공사"
SOURCE_YEAR = 2024
SOURCE_ORG = "왕산"


def parse_num(s):
    if not s: return 0
    s = str(s).replace(',', '').replace(' ', '').replace('%', '').strip()
    m = re.search(r'-?[\d.]+', s)
    return float(m.group()) if m else 0


def get_pg():
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"), port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"), user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"), sslmode="require")


def extract_proposal_page(text, page_num):
    lines = text.split('\n')
    d = {
        'source_page': page_num,
        'alt_number_raw': '', 'field': '', 'proposal_title': '',
        'original_desc': '', 'alternative_desc': '',
        'advantages': '', 'disadvantages': '',
        'cost_original': 0, 'cost_alternative': 0, 'cost_savings': 0,
    }

    # [대안-XX] 제안명 — 첫 줄에서 추출
    for line in lines:
        m = re.match(r'\[대안-(\d+)\]\s*(.*)', line.strip())
        if m:
            d['alt_number_raw'] = f"대안-{m.group(1)}"
            d['proposal_title'] = m.group(2).strip()
            break

    # 분야 추출
    field_kw = {'건축': ['골조', '벽체', '슬라브', '방수', '단열', '마감', '창호', '도어', '셔터', '블록', '천창', '계단'],
                '구조': ['구조', '철근', '기초', 'PC', 'PHC', '파일'],
                '기계': ['급수', '배관', '냉난방', '환기', '급탕', '소방', '펌프', '밸브'],
                '전기': ['전기', '조명', '수배전', '변압기', '콘센트', '분전반', '케이블'],
                '토목': ['토목', '포장', '우수', '배수', '옹벽', '맨홀'],
                '조경': ['조경', '식재', '잔디']}
    title = d['proposal_title']
    for field, kws in field_kw.items():
        if any(k in title for k in kws):
            d['field'] = field
            break
    if not d['field']:
        d['field'] = '건축'

    # 원안/대안 설명
    in_orig = False; in_alt = False
    orig_lines = []; alt_lines = []
    for i, line in enumerate(lines):
        ls = line.strip()
        if ls == '원안':
            in_orig = True; in_alt = False; continue
        if ls == '대안':
            in_orig = False; in_alt = True; continue
        if ls in ('제안의', '특성', '장 점', '단 점', '효   과', '비용분석'): 
            in_orig = False; in_alt = False
        if ls in ('개', '요', '도', '설', '명', '', '구분', '개요'): continue
        if in_orig and ls and not ls.startswith('※'):
            orig_lines.append(ls.replace('∙', '').replace('·', '').strip())
        elif in_alt and ls and not ls.startswith('※'):
            alt_lines.append(ls.replace('∙', '').replace('·', '').strip())
    d['original_desc'] = ' '.join(orig_lines)[:400]
    d['alternative_desc'] = ' '.join(alt_lines)[:400]

    # 장점
    for i, line in enumerate(lines):
        if '장 점' in line.strip() or '장  점' in line.strip():
            adv = []
            for j in range(i+1, min(i+5, len(lines))):
                ls = lines[j].strip()
                if ls in ('단 점', '시공시', '-', '', '효   과'): break
                adv.append(ls.replace('∙','').strip())
            d['advantages'] = ' '.join(adv)[:200]
            break

    # 비용 — 이 포맷에서는 같은 페이지에 비용이 있을 수 있음
    for i, line in enumerate(lines):
        if '증감액' in line.strip() or '절감액' in line.strip():
            for j in range(i, min(i+3, len(lines))):
                for n in re.findall(r'[\d,]+', lines[j]):
                    val = parse_num(n)
                    if val >= 1000:
                        d['cost_savings'] = val
                        break
                if d['cost_savings'] > 0: break
            break

    # 원안비용/대안비용
    for i, line in enumerate(lines):
        ls = line.strip()
        if '원안비용' in ls or '원안 비용' in ls:
            nums = re.findall(r'[\d,]+', ls)
            for n in nums:
                val = parse_num(n)
                if val >= 1000: d['cost_original'] = val; break
        if '대안비용' in ls or '대안 비용' in ls:
            nums = re.findall(r'[\d,]+', ls)
            for n in nums:
                val = parse_num(n)
                if val >= 1000: d['cost_alternative'] = val; break

    return d


def extract_perf_page(text):
    """성능 세부 평가 페이지 — 7항목"""
    categories = ['시공성', '유지관리성', '공간활용성', '독창성', '편의성', '안전성', '환경']
    perf_scores = []
    lines = text.split('\n')
    
    for cat in categories:
        for i, line in enumerate(lines):
            if cat in line.strip():
                nums = []
                for j in range(max(0,i-1), min(i+4, len(lines))):
                    for n in re.findall(r'\d+', lines[j]):
                        nums.append(int(n))
                if len(nums) >= 4:
                    perf_scores.append({
                        'category': cat if cat != '환경' else '환경/경관성',
                        'original_score': nums[-2] if len(nums) >= 2 else 0,
                        'alternative_score': nums[-1] if len(nums) >= 1 else 0,
                    })
                break
    
    # 성능점수 합계
    perf_orig = 0; perf_alt = 0
    for i, line in enumerate(lines):
        if '성능점수' in line.strip() or '합계' in line.strip():
            nums = re.findall(r'\d+', line)
            big_nums = [int(n) for n in nums if int(n) >= 100]
            if len(big_nums) >= 2:
                perf_orig = big_nums[0]
                perf_alt = big_nums[1]
            break
    
    return perf_scores, perf_orig, perf_alt


def insert_to_supabase(all_data):
    pg = get_pg(); cur = pg.cursor()
    cur.execute("""INSERT INTO projects (project_id, project_name, file_path, total_alternatives, source_file, source_year, source_org)
        VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (project_id) DO UPDATE SET total_alternatives = EXCLUDED.total_alternatives""",
        (PROJECT_ID, PROJECT_NAME, str(PDF_PATH), len(all_data), PDF_PATH.name, SOURCE_YEAR, SOURCE_ORG))
    cur.execute("SELECT COALESCE(MAX(alt_number), 0) FROM alternatives")
    max_num = cur.fetchone()[0]
    for i, d in enumerate(all_data):
        alt_num = max_num + i + 1
        alt_id = f"wangsan_{alt_num:03d}"
        cur.execute("""INSERT INTO alternatives (
                alt_id, project_id, alt_number, proposal_title,
                original_description, alternative_description,
                advantages, disadvantages, project_name, source_page,
                field_category, value_type_corrected, how2_code, how2_name, space
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (alt_id) DO NOTHING""",
            (alt_id, PROJECT_ID, alt_num, d['proposal_title'],
             d['original_desc'], d['alternative_desc'],
             d['advantages'], d.get('disadvantages',''), PROJECT_NAME, d['source_page'],
             d['field'], '비용절감형',
             d.get('how2_code',''), d.get('how2_name',''), d.get('space','')))
        savings = d.get('cost_savings', 0)
        savings_rate = round(savings / d['cost_original'] * 100, 2) if d.get('cost_original', 0) > 0 else 0
        cur.execute("""INSERT INTO cost_evaluations (alt_id, cost_type, original_cost, alternative_cost, savings_amount, savings_rate)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (alt_id, 'project_initial', d.get('cost_original',0)/1000000, d.get('cost_alternative',0)/1000000,
             savings/1000000, savings_rate))
        cur.execute("""INSERT INTO value_evaluations (alt_id, performance_original, performance_alternative,
                performance_change_rate, cost_change_rate, value_change_rate)
            VALUES (%s,%s,%s,%s,%s,%s)""",
            (alt_id, d.get('perf_orig',0), d.get('perf_alt',0), 0, savings_rate, 0))
        for ps in d.get('perf_scores', []):
            cur.execute("""INSERT INTO performance_scores (alt_id, category, original_score, alternative_score, score_delta)
                VALUES (%s,%s,%s,%s,%s)""",
                (alt_id, ps['category'], ps['original_score'], ps['alternative_score'],
                 ps['alternative_score'] - ps['original_score']))
    pg.commit(); pg.close()
    return max_num + 1, max_num + len(all_data)


def run():
    print("=" * 60, flush=True)
    print("왕산2초중통합 신축 — 대안구체화 추출", flush=True)
    print("=" * 60, flush=True)

    doc = fitz.open(str(PDF_PATH))
    pages = len(doc)
    print(f"  총 {pages} 페이지", flush=True)

    sys.path.insert(0, str(BASE_DIR))
    from src.cube_taxonomy import classify_how2, classify_space

    # Phase 1: 모든 페이지에서 [대안-XX] 패턴 감지하여 proposal/perf 페이지 매핑
    proposal_pages = {}  # alt_num -> page_idx
    perf_pages = {}      # alt_num -> [page_idx, ...]

    for i in range(pages):
        text = doc[i].get_text()
        alts = re.findall(r'\[대안-(\d+)\]', text)
        if not alts:
            continue
        alt_num = int(alts[0])
        first_line = text.split('\n')[0].strip()
        if '성능 세부 평가' in first_line or '성능세부평가' in first_line:
            perf_pages.setdefault(alt_num, []).append(i)
        else:
            proposal_pages[alt_num] = i

    print(f"  대안 페이지: {len(proposal_pages)}건, 성능 페이지: {sum(len(v) for v in perf_pages.values())}건", flush=True)

    # Phase 2: 추출
    all_data = []
    seen = set()
    for alt_num in sorted(set(list(proposal_pages.keys()) + list(perf_pages.keys()))):
        if alt_num in seen:
            continue
        seen.add(alt_num)

        d = None
        if alt_num in proposal_pages:
            pg_idx = proposal_pages[alt_num]
            text1 = doc[pg_idx].get_text()
            d = extract_proposal_page(text1, pg_idx + 1)
        
        if d is None or not d['proposal_title']:
            # 성능 페이지에서만 제목 추출 시도
            if alt_num in perf_pages:
                pg_idx = perf_pages[alt_num][0]
                text = doc[pg_idx].get_text()
                m = re.search(r'\[대안-\d+\]\s*(.*)', text)
                title = m.group(1).strip() if m else f'대안-{alt_num}'
                d = {
                    'source_page': pg_idx + 1, 'alt_number_raw': f'대안-{alt_num}',
                    'field': '건축', 'proposal_title': title,
                    'original_desc': '', 'alternative_desc': '',
                    'advantages': '', 'disadvantages': '',
                    'cost_original': 0, 'cost_alternative': 0, 'cost_savings': 0,
                }
            else:
                continue

        # 성능 페이지 병합
        if alt_num in perf_pages:
            for perf_pg in perf_pages[alt_num]:
                text2 = doc[perf_pg].get_text()
                perf_scores, perf_orig, perf_alt = extract_perf_page(text2)
                if perf_scores:
                    d['perf_scores'] = perf_scores
                    d['perf_orig'] = perf_orig
                    d['perf_alt'] = perf_alt
                    break

        # CUBE
        title_text = d['proposal_title'] + ' ' + d.get('original_desc','') + ' ' + d.get('alternative_desc','')
        how2_list = classify_how2(title_text)
        if how2_list:
            h = how2_list[0]
            d['how2_code'] = f"{h[0]}-{h[1]}" if len(h) >= 2 else ''
            d['how2_name'] = h[2] if len(h) >= 3 else ''
        else:
            d['how2_code'] = ''; d['how2_name'] = ''
        space_list = classify_space(title_text)
        d['space'] = space_list[0] if isinstance(space_list, list) and space_list else ''

        json_path = OUT_DIR / f"wangsan_{len(all_data)+1:03d}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2, default=str)
        all_data.append(d)

    print(f"  {len(all_data)}건 추출", flush=True)

    if not all_data:
        print("  추출 데이터 없음.", flush=True)
        doc.close(); return

    print(f"  DB 적재 중...", flush=True)
    start, end = insert_to_supabase(all_data)

    fields = {}
    for d in all_data: fields[d['field']] = fields.get(d['field'], 0) + 1
    perf_count = sum(1 for d in all_data if d.get('perf_scores'))

    doc.close()
    print(f"\n{'='*60}", flush=True)
    print(f"  총 추출: {len(all_data)}건", flush=True)
    print(f"  분야별: {fields}", flush=True)
    print(f"  성능평가: {perf_count}건", flush=True)
    print(f"  대안: #{start} ~ #{end}", flush=True)


if __name__ == "__main__":
    run()
