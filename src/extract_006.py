"""
퇴계동 국민체육센터 건립 — 5개 분야 PDF 추출기 (006)
=====================================================
- 2페이지/제안: 홀수(대안정보), 짝수(비용산출)
- 한글 정상 추출
- 5개 파일: 건축, 구조, 기계, 전기, 토목
"""
import fitz, json, re, sys, io, os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

RAW_DIR = BASE_DIR / ".raw_data"
OUT_DIR = BASE_DIR / "data" / "extracted_006"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ID = "toegye_sports_2024"
PROJECT_NAME = "퇴계동 국민체육센터 건립공사"
SOURCE_YEAR = 2024
SOURCE_ORG = "퇴계동"

FILES = [
    ("건축", RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_건축.pdf"),
    ("구조", RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_구조.pdf"),
    ("기계", RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_기계.pdf"),
    ("전기", RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_전기.pdf"),
    ("토목", RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_토목.pdf"),
]


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


def extract_proposal_page(text):
    """대안 정보 페이지 추출"""
    lines = text.split('\n')
    d = {
        'alt_number_raw': '', 'field_code': '', 'field': '',
        'proposal_title': '', 'original_desc': '', 'alternative_desc': '',
        'advantages': '', 'disadvantages': '', 'designer_opinion': '',
        'accepted': False,
    }

    for i, line in enumerate(lines):
        ls = line.strip()

        # 대안번호
        if ls.startswith('대안-') and not d['alt_number_raw']:
            d['alt_number_raw'] = ls
        
        # 분야 코드 (예: [건축-01])
        m = re.search(r'\[(.+?)\]', ls)
        if m and not d['field_code']:
            d['field_code'] = m.group(1)
        
        # 분야
        if ls in ('건축', '구조', '기계', '전기', '토목', '조경', '소방'):
            if not d['field']:
                d['field'] = ls

        # 대안명
        if '대 안 명' in ls:
            if i + 1 < len(lines):
                d['proposal_title'] = lines[i + 1].strip()

    # 원안 설명 — '원안' 다음 '설명' 섹션
    in_original = False
    in_alternative = False
    orig_lines = []
    alt_lines = []

    for i, line in enumerate(lines):
        ls = line.strip()
        if ls == '원안':
            in_original = True; in_alternative = False; continue
        if ls == '대안':
            in_original = False; in_alternative = True; continue
        if ls in ('제안의', '특성', '장 점', '단 점', '설계자', '검토의견'):
            in_original = False; in_alternative = False
        if ls in ('개', '요', '도', '설', '명'):
            continue
        if in_original and ls and ls != '∙' and not ls.startswith('※'):
            orig_lines.append(ls.replace('∙', '').strip())
        elif in_alternative and ls and ls != '∙' and not ls.startswith('※'):
            alt_lines.append(ls.replace('∙', '').strip())

    d['original_desc'] = ' '.join(orig_lines)[:400]
    d['alternative_desc'] = ' '.join(alt_lines)[:400]

    # 장점
    for i, line in enumerate(lines):
        if '장 점' in line.strip() or '장  점' in line.strip():
            adv_lines = []
            for j in range(i + 1, min(i + 5, len(lines))):
                ls = lines[j].strip()
                if ls in ('단 점', '시공시', '-', ''): break
                adv_lines.append(ls.replace('∙', '').strip())
            d['advantages'] = ' '.join(adv_lines)[:200]
            break

    # 단점
    for i, line in enumerate(lines):
        if '단 점' in line.strip() or '단  점' in line.strip():
            dis_lines = []
            for j in range(i + 1, min(i + 5, len(lines))):
                ls = lines[j].strip()
                if ls in ('시공시', '설계자', '-', ''): break
                dis_lines.append(ls.replace('∙', '').strip())
            d['disadvantages'] = ' '.join(dis_lines)[:200]
            break

    # 설계자 검토의견
    for i, line in enumerate(lines):
        if '검토의견' in line.strip():
            opinion_lines = []
            for j in range(i + 1, min(i + 5, len(lines))):
                ls = lines[j].strip()
                if ls.startswith('※') or ls in ('반영', '미반영', '◎'): break
                opinion_lines.append(ls.replace('∙', '').strip())
            d['designer_opinion'] = ' '.join(opinion_lines)[:300]
            break

    # 반영 여부
    d['accepted'] = '◎' in text and '반영' in text

    return d


def extract_cost_page(text):
    """비용산출 페이지 추출"""
    d = {'cost_original': 0, 'cost_alternative': 0, 'cost_savings': 0}
    lines = text.split('\n')

    # ④총계 행
    for i, line in enumerate(lines):
        ls = line.strip()
        if '총계' in ls or '④' in ls:
            nums = []
            for j in range(i, min(i + 3, len(lines))):
                for n in re.findall(r'[\d,]+', lines[j]):
                    val = parse_num(n)
                    if val >= 1000:
                        nums.append(val)
            if len(nums) >= 2:
                d['cost_original'] = nums[0]
                d['cost_alternative'] = nums[1]
            elif len(nums) == 1:
                d['cost_original'] = nums[0]
            break

    # 증감액
    for i, line in enumerate(lines):
        if '증감액' in line.strip():
            for j in range(i, min(i + 3, len(lines))):
                nums = re.findall(r'[\d,]+', lines[j])
                for n in nums:
                    val = parse_num(n)
                    if val >= 1000:
                        d['cost_savings'] = val
                        break
                if d['cost_savings'] > 0:
                    break
            break

    return d


def process_all_files():
    print("=" * 60, flush=True)
    print("퇴계동 국민체육센터 건립 — 5개 분야 추출", flush=True)
    print("=" * 60, flush=True)

    sys.path.insert(0, str(BASE_DIR))
    from src.cube_taxonomy import classify_how2, classify_space

    all_data = []

    for field_name, pdf_path in FILES:
        doc = fitz.open(str(pdf_path))
        pages = len(doc)
        print(f"\n  [{field_name}] {pages} 페이지", flush=True)

        # 2페이지 페어로 순회
        for pg_idx in range(0, pages, 2):
            text1 = doc[pg_idx].get_text()

            # 대안 페이지인지 확인
            if '대안번호' not in text1 and '대 안 명' not in text1:
                continue

            d1 = extract_proposal_page(text1)

            # 비용 페이지 (다음 페이지)
            d2 = {}
            if pg_idx + 1 < pages:
                text2 = doc[pg_idx + 1].get_text()
                if '비용' in text2:
                    d2 = extract_cost_page(text2)

            # 병합
            d = {
                'source_page': pg_idx + 1,
                'source_file': pdf_path.name,
                'alt_number_raw': d1['alt_number_raw'],
                'field_code': d1['field_code'],
                'field': d1['field'] or field_name,
                'proposal_title': d1['proposal_title'],
                'original_desc': d1['original_desc'],
                'alternative_desc': d1['alternative_desc'],
                'advantages': d1['advantages'],
                'disadvantages': d1['disadvantages'],
                'designer_opinion': d1['designer_opinion'],
                'accepted': d1['accepted'],
                'cost_original': d2.get('cost_original', 0),
                'cost_alternative': d2.get('cost_alternative', 0),
                'cost_savings': d2.get('cost_savings', 0),
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
            json_path = OUT_DIR / f"toegye_{len(all_data)+1:03d}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=2)

            all_data.append(d)

        doc.close()

    print(f"\n  총 {len(all_data)}건 추출 완료", flush=True)
    return all_data


def insert_to_supabase(all_data):
    pg = get_pg(); cur = pg.cursor()
    cur.execute("""INSERT INTO projects (project_id, project_name, file_path, total_alternatives, source_file, source_year, source_org)
        VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (project_id) DO UPDATE SET total_alternatives = EXCLUDED.total_alternatives""",
        (PROJECT_ID, PROJECT_NAME, str(RAW_DIR), len(all_data), '005_퇴계동_*.pdf', SOURCE_YEAR, SOURCE_ORG))
    cur.execute("SELECT COALESCE(MAX(alt_number), 0) FROM alternatives")
    max_num = cur.fetchone()[0]

    for i, d in enumerate(all_data):
        alt_num = max_num + i + 1
        alt_id = f"toegye_{alt_num:03d}"

        field_map = {'건축': '건축공사', '구조': '건축공사', '기계': '기계설비공사', '전기': '전기공사', '토목': '토목공사'}
        how1 = field_map.get(d['field'], d['field'])

        cur.execute("""INSERT INTO alternatives (
                alt_id, project_id, alt_number, proposal_title,
                original_description, alternative_description,
                advantages, disadvantages, project_name, source_page,
                field_category, value_type_corrected, how2_code, how2_name, space
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (alt_id) DO NOTHING""",
            (alt_id, PROJECT_ID, alt_num, d['proposal_title'],
             d['original_desc'], d['alternative_desc'],
             d['advantages'], d['disadvantages'], PROJECT_NAME, d['source_page'],
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
            (alt_id, 0, 0, 0, savings_rate, 0))

    pg.commit(); pg.close()
    return max_num + 1, max_num + len(all_data)


def run():
    all_data = process_all_files()
    if not all_data:
        print("  추출 데이터 없음.", flush=True)
        return

    print(f"\n  DB 적재 중...", flush=True)
    start, end = insert_to_supabase(all_data)
    print(f"  대안 #{start}~#{end} 적재 완료", flush=True)

    fields = {}
    for d in all_data:
        fields[d['field']] = fields.get(d['field'], 0) + 1
    cost_count = sum(1 for d in all_data if d.get('cost_savings', 0) > 0)

    print(f"\n{'='*60}", flush=True)
    print(f"  총 추출: {len(all_data)}건", flush=True)
    print(f"  분야별: {fields}", flush=True)
    print(f"  비용절감 있음: {cost_count}건", flush=True)
    print(f"  대안: #{start} ~ #{end}", flush=True)


if __name__ == "__main__":
    run()
