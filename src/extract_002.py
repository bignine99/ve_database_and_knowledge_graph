"""
서울특별시 2022 VE 사례집 추출기
=================================
001_서울특별시_2022년_건설공사_설계경제성(VE)_검토_사례집(원본).pdf
- 474페이지, 131건 VE 대안, ~35개 프로젝트
- 1페이지/대안 구조
"""

import fitz
import json
import re
import sys
import io
import sqlite3
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "db" / "ve_database.sqlite"
PDF_PATH = BASE_DIR / ".raw_data" / "001_서울특별시_2022년_건설공사_설계경제성(VE)_검토_사례집(원본).pdf"
OUT_DIR = BASE_DIR / "data" / "extracted_002"
IMG_DIR = BASE_DIR / "data" / "images_002"

OUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)


def upgrade_schema():
    """DB 스키마에 project_name, source_page, field_category 추가."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # alternatives 테이블 보강
    existing = [r[1] for r in cur.execute("PRAGMA table_info(alternatives)").fetchall()]
    if "project_name" not in existing:
        cur.execute("ALTER TABLE alternatives ADD COLUMN project_name TEXT DEFAULT ''")
        print("  ✅ Added: alternatives.project_name")
    if "source_page" not in existing:
        cur.execute("ALTER TABLE alternatives ADD COLUMN source_page INTEGER DEFAULT 0")
        print("  ✅ Added: alternatives.source_page")
    if "field_category" not in existing:
        cur.execute("ALTER TABLE alternatives ADD COLUMN field_category TEXT DEFAULT ''")
        print("  ✅ Added: alternatives.field_category")

    # projects 테이블 보강
    existing_p = [r[1] for r in cur.execute("PRAGMA table_info(projects)").fetchall()]
    if "source_file" not in existing_p:
        cur.execute("ALTER TABLE projects ADD COLUMN source_file TEXT DEFAULT ''")
        print("  ✅ Added: projects.source_file")
    if "source_year" not in existing_p:
        cur.execute("ALTER TABLE projects ADD COLUMN source_year INTEGER DEFAULT 0")
        print("  ✅ Added: projects.source_year")
    if "source_org" not in existing_p:
        cur.execute("ALTER TABLE projects ADD COLUMN source_org TEXT DEFAULT ''")
        print("  ✅ Added: projects.source_org")

    conn.commit()
    conn.close()
    print("  Schema upgrade complete.\n")


def detect_projects(doc):
    """프로젝트 소개 페이지를 감지하여 프로젝트 목록 생성."""
    projects = []

    for i in range(len(doc)):
        text = doc[i].get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # 프로젝트 구분 페이지 패턴: 번호 + 프로젝트명 + 기간 + 위치도
        if '위치도' in text and len(lines) > 3:
            # 프로젝트명 추출 시도
            proj_name = ''
            for l in lines:
                if any(kw in l for kw in ['건설공사', '사업', '공사', '정비', '건립', '신축', '개선', '보완']):
                    if '설계경제성' not in l and '사례집' not in l and len(l) > 5:
                        proj_name = l.strip()
                        break
            if not proj_name:
                # 두 번째 줄이 프로젝트명인 경우
                for l in lines[1:5]:
                    if len(l) > 8 and '위치도' not in l and '장' not in l[:2]:
                        proj_name = l.strip()
                        break

            if proj_name:
                projects.append({
                    'page': i + 1,
                    'name': proj_name[:80],
                    'proposals': []
                })

    return projects


def detect_proposals(doc):
    """1페이지짜리 VE 대표 제안 페이지를 감지."""
    proposals = []

    for i in range(len(doc)):
        text = doc[i].get_text()

        # 대표 제안 페이지 패턴: "제 안 명" + "개 선 전/후" + "비용변화" 모두 존재
        if '제 안 명' in text and ('개 선 전' in text or '개선전' in text) and '비용변화' in text:
            proposals.append({
                'page': i + 1,
                'text': text
            })

    return proposals


def extract_proposal_data(text, page_num):
    """1페이지 제안 텍스트에서 구조화된 데이터 추출."""
    data = {
        'source_page': page_num,
        'proposal_title': '',
        'original_description': '',
        'alternative_description': '',
        'advantages': '',
        'disadvantages': '',
        'implementation_notes': '',
        'effect': '',
        'cost': {
            'initial_before': 0, 'initial_after': 0,
            'maint_before': 0, 'maint_after': 0,
            'lcc_before': 0, 'lcc_after': 0,
            'savings': 0, 'savings_rate': 0,
        },
        'performance': {
            'p1': 500.0, 'p2': 500.0,
            'v1': 500.0, 'v2': 500.0,
            'value_improvement': 0,
        },
    }

    lines = text.split('\n')

    # 제안명 추출
    for line in lines:
        if '•' in line and '제 안 명' not in line and len(line.strip()) > 5:
            data['proposal_title'] = line.replace('•', '').strip()
            break

    # 개선전/후 내용 추출
    in_before = False
    in_after = False
    for line in lines:
        line_s = line.strip()
        if '제안내용' in line_s:
            in_before = True
            continue
        if '개요도' in line_s:
            in_before = False
            in_after = False
            break
        if in_before and '•' in line_s:
            if not data['original_description']:
                data['original_description'] = line_s.replace('•', '').strip()
                in_after = True
            elif in_after:
                data['alternative_description'] = line_s.replace('•', '').strip()
                in_before = False

    # 숫자 추출 함수
    def parse_num(s):
        if not s:
            return 0
        s = s.replace(',', '').replace(' ', '').strip()
        try:
            return float(s)
        except:
            return 0

    # 비용 데이터 추출 (개선전/후 행)
    # 패턴: "개 선 전" 다음에 숫자들, "개 선 후" 다음에 숫자들
    nums_before = []
    nums_after = []
    found_before = False
    found_after = False

    for line in lines:
        line_s = line.strip()

        if '개 선 전' in line_s and '제안내용' not in text[max(0, text.index(line_s)-100):text.index(line_s)]:
            found_before = True
            found_after = False
            # 같은 줄에 숫자가 있을 수 있음
            nums = re.findall(r'[\d,]+\.?\d*', line_s.replace('개 선 전', ''))
            nums_before.extend(nums)
            continue

        if '개 선 후' in line_s and found_before:
            found_after = True
            found_before = False
            nums = re.findall(r'[\d,]+\.?\d*', line_s.replace('개 선 후', ''))
            nums_after.extend(nums)
            continue

        if found_before and not found_after:
            nums = re.findall(r'[\d,]+\.?\d*', line_s)
            nums_before.extend(nums)

        if found_after:
            nums = re.findall(r'[\d,]+\.?\d*', line_s)
            nums_after.extend(nums)
            if len(nums_after) >= 3:
                found_after = False

    # L1, L2 패턴
    l1_match = re.search(r'L1\s*=\s*([\d,]+\.?\d*)', text)
    l2_match = re.search(r'L2\s*=\s*([\d,]+\.?\d*)', text)
    if l1_match:
        data['cost']['lcc_before'] = parse_num(l1_match.group(1))
    if l2_match:
        data['cost']['lcc_after'] = parse_num(l2_match.group(1))

    # 절감액
    savings_match = re.search(r'절감[액률].*?(-?[\d,]+\.?\d*)', text.replace('\n', ' '))
    if savings_match:
        data['cost']['savings'] = parse_num(savings_match.group(1))

    # 절감률
    rate_match = re.search(r'(\d+\.?\d*)%', text.split('절감률')[1] if '절감률' in text else '')
    if rate_match:
        data['cost']['savings_rate'] = parse_num(rate_match.group(1))

    # 성능/가치 점수
    p1_match = re.search(r'P1\s*=\s*([\d,]+\.?\d*)', text)
    p2_match = re.search(r'P2\s*=\s*([\d,]+\.?\d*)', text)
    v1_match = re.search(r'V1\s*=\s*([\d,]+\.?\d*)', text)
    v2_match = re.search(r'V2\s*=\s*([\d,]+\.?\d*)', text)

    if p1_match: data['performance']['p1'] = parse_num(p1_match.group(1))
    if p2_match: data['performance']['p2'] = parse_num(p2_match.group(1))
    if v1_match: data['performance']['v1'] = parse_num(v1_match.group(1))
    if v2_match: data['performance']['v2'] = parse_num(v2_match.group(1))

    # 가치향상도
    vi_match = re.search(r'(\d+\.?\d*)\s*%', text.split('V1}×100%)')[-1] if 'V1}×100%)' in text else '')
    if vi_match:
        data['performance']['value_improvement'] = parse_num(vi_match.group(1))

    # 장점/단점/이행시 주의할 점
    sections = text.split('제안의')
    if len(sections) > 1:
        feat_text = sections[1]
        for line in feat_text.split('\n'):
            line_s = line.strip()
            if '•' in line_s:
                if '장 점' not in feat_text[:feat_text.index(line_s)] if line_s in feat_text else True:
                    if not data['advantages']:
                        data['advantages'] = line_s.replace('•', '').strip()
                    elif not data['disadvantages']:
                        data['disadvantages'] = line_s.replace('•', '').strip()

    # 효과
    effect_parts = text.split('효 과')
    if len(effect_parts) > 1:
        for line in effect_parts[-1].split('\n'):
            if '•' in line:
                data['effect'] = line.replace('•', '').strip()
                break

    # 초기공사비 추출 (nums_before/after에서)
    if nums_before:
        data['cost']['initial_before'] = parse_num(nums_before[0])
    if nums_after:
        data['cost']['initial_after'] = parse_num(nums_after[0])

    return data


def extract_image(doc, page_idx, alt_num):
    """페이지에서 개요도 이미지 추출."""
    page = doc[page_idx]
    images = page.get_images(full=True)
    saved = []

    alt_dir = IMG_DIR / f"alt_{alt_num:03d}"
    alt_dir.mkdir(exist_ok=True)

    for idx, img_info in enumerate(images):
        xref = img_info[0]
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n > 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)

            img_type = 'original_diagram' if idx == 0 else 'alternative_diagram' if idx == 1 else f'diagram_{idx}'
            img_path = alt_dir / f"alt_{alt_num:03d}_{img_type}.png"
            pix.save(str(img_path))
            saved.append({
                'type': img_type,
                'path': str(img_path),
                'width': pix.width,
                'height': pix.height,
            })
            pix = None
        except Exception as e:
            pass

    return saved


def map_project_to_proposal(projects, proposal_page):
    """제안 페이지 번호로 소속 프로젝트 결정."""
    best = None
    for p in projects:
        if p['page'] <= proposal_page:
            best = p
        else:
            break
    return best['name'] if best else '서울특별시 2022 VE 사례집'


def classify_field(title, text):
    """제안명/텍스트에서 분야 분류."""
    civil_kw = ['토목', '구조', '토질', '터널', '교량', '도로', '지하철', '철도', '배수', '하수', '상수',
                 '옹벽', '흙막이', '파일', 'CIP', '굴착', '지보', '록볼트', '철근', '콘크리트', 'BOX']
    arch_kw = ['건축', '시공', '마감', '석재', '창호', '방수', '벽체', '천장', '도장', '타일',
               '바닥', '지붕', '외벽', '내벽', '단열', '유리', '커튼월', '석고보드', '캐노피']
    mep_kw = ['기계', '전기', '설비', '공조', '냉방', '난방', '환기', '소방', '배관', '펌프',
              '조명', '수전', '소화', '급수', '급배수', '케이블', '변전', '수배전', '팬']

    combined = title + ' ' + text[:300]
    c_score = sum(1 for k in civil_kw if k in combined)
    a_score = sum(1 for k in arch_kw if k in combined)
    m_score = sum(1 for k in mep_kw if k in combined)

    if m_score > max(c_score, a_score):
        return '설비'
    elif a_score > c_score:
        return '건축'
    else:
        return '토목'


def insert_to_db(all_data, project_info):
    """추출된 데이터를 DB에 INSERT."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 새 프로젝트 등록
    cur.execute("""
        INSERT INTO projects (project_name, file_path, total_alternatives, source_file, source_year, source_org)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        '서울특별시 2022년 건설공사 VE 검토 사례집',
        str(PDF_PATH),
        len(all_data),
        PDF_PATH.name,
        2022,
        '서울특별시',
    ))
    project_id = cur.lastrowid

    # 기존 최대 alt_number 확인
    max_num = cur.execute("SELECT COALESCE(MAX(alt_number), 0) FROM alternatives").fetchone()[0]

    for i, d in enumerate(all_data):
        alt_num = max_num + i + 1

        cur.execute("""
            INSERT INTO alternatives (
                project_id, alt_number, proposal_title,
                original_description, alternative_description,
                advantages, disadvantages, implementation_notes, analysis_summary,
                project_name, source_page, field_category,
                how2_code, how2_name, space, value_type_corrected
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id, alt_num, d['proposal_title'],
            d['original_description'], d['alternative_description'],
            d['advantages'], d['disadvantages'], d['implementation_notes'], d['effect'],
            d['project_name'], d['source_page'], d['field_category'],
            d.get('how2_code', ''), d.get('how2_name', ''), d.get('space', ''), d.get('value_type', ''),
        ))
        alt_id = cur.lastrowid

        # 비용 데이터
        c = d['cost']
        for ctype, orig, alt_c in [
            ('project_initial', c['initial_before'], c['initial_after']),
            ('project_lifecycle', c['lcc_before'], c['lcc_after']),
        ]:
            cur.execute("""
                INSERT INTO cost_evaluations (alt_id, cost_type, original_cost, alternative_cost, savings_amount, savings_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (alt_id, ctype, orig, alt_c, orig - alt_c, c['savings_rate']))

        # 가치 평가
        perf = d['performance']
        perf_change = round((perf['p2'] - perf['p1']) / perf['p1'] * 100, 2) if perf['p1'] > 0 else 0
        cost_change = round(c['savings_rate'], 2)
        value_change = round(perf['value_improvement'], 2)

        cur.execute("""
            INSERT INTO value_evaluations (
                alt_id, performance_original, performance_alternative,
                performance_change_rate, cost_change_rate, value_change_rate
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (alt_id, perf['p1'], perf['p2'], perf_change, cost_change, value_change))

        # 이미지 데이터
        for img in d.get('images', []):
            cur.execute("""
                INSERT INTO images (alt_id, image_type, file_path, width, height)
                VALUES (?, ?, ?, ?, ?)
            """, (alt_id, img['type'], img['path'], img['width'], img['height']))

    conn.commit()
    conn.close()
    return max_num + 1, max_num + len(all_data)


def run():
    """메인 파이프라인."""
    print("=" * 60)
    print("서울특별시 2022 VE 사례집 추출 파이프라인")
    print("=" * 60)

    # 1. 스키마 보강
    print("\n[1/5] DB 스키마 보강...")
    upgrade_schema()

    # 2. PDF 열기
    print("[2/5] PDF 분석 중...")
    doc = fitz.open(str(PDF_PATH))
    print(f"  총 {len(doc)} 페이지")

    # 3. 프로젝트/제안 감지
    print("[3/5] 프로젝트 및 제안 감지...")
    projects = detect_projects(doc)
    proposals = detect_proposals(doc)
    print(f"  프로젝트: {len(projects)}개")
    print(f"  VE 대표 제안: {len(proposals)}개")

    # 4. 데이터 추출
    print(f"\n[4/5] {len(proposals)}건 데이터 추출 중...")

    # CUBE 분류를 위해 cube_taxonomy 로드
    sys.path.insert(0, str(BASE_DIR))
    from src.cube_taxonomy import classify_how2, classify_space

    def classify_value_type(p1, p2, lcc1, lcc2):
        perf_up = p2 > p1
        cost_down = lcc2 < lcc1
        if perf_up and cost_down:
            return '가치혁신형'
        elif perf_up and not cost_down:
            return '성능강조형'
        elif not perf_up and cost_down:
            return '비용절감형'
        else:
            return '성능향상형'

    all_data = []
    for idx, prop in enumerate(proposals):
        d = extract_proposal_data(prop['text'], prop['page'])
        d['project_name'] = map_project_to_proposal(projects, prop['page'])
        d['field_category'] = classify_field(d['proposal_title'], prop['text'])

        # CUBE 분류
        title_text = d['proposal_title'] + ' ' + d['original_description'] + ' ' + d['alternative_description']
        how2_list = classify_how2(title_text)
        if how2_list and len(how2_list) > 0:
            h = how2_list[0]  # (how1, how2_code, how2_name)
            d['how2_code'] = f"{h[0]}-{h[1]}" if len(h) >= 2 else ''
            d['how2_name'] = h[2] if len(h) >= 3 else ''
        else:
            d['how2_code'] = ''
            d['how2_name'] = ''
        space_list = classify_space(title_text)
        d['space'] = space_list[0] if isinstance(space_list, list) and space_list else (space_list if isinstance(space_list, str) else '')
        d['value_type'] = classify_value_type(
            d['performance']['p1'], d['performance']['p2'],
            d['cost']['lcc_before'], d['cost']['lcc_after']
        )

        # 이미지 추출
        d['images'] = extract_image(doc, prop['page'] - 1, len(all_data) + 108)  # 기존 107개 이후

        # JSON 저장
        json_path = OUT_DIR / f"alt_{len(all_data) + 108:03d}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

        all_data.append(d)

        if (idx + 1) % 20 == 0:
            print(f"  ... {idx + 1}/{len(proposals)} 완료")

    print(f"  ✅ {len(all_data)}건 추출 완료")

    # 5. DB 적재
    print(f"\n[5/5] DB 적재 중...")
    start_num, end_num = insert_to_db(all_data, projects)
    print(f"  ✅ 대안 #{start_num}~#{end_num} 적재 완료")

    # 통계
    doc.close()
    fields = {}
    for d in all_data:
        fields[d['field_category']] = fields.get(d['field_category'], 0) + 1

    print(f"\n{'='*60}")
    print(f"추출 완료 요약")
    print(f"{'='*60}")
    print(f"  총 추출: {len(all_data)}건")
    print(f"  분야별: {fields}")
    print(f"  이미지: {sum(len(d.get('images',[])) for d in all_data)}장")
    print(f"  DB 대안 번호: #{start_num} ~ #{end_num}")
    print(f"  JSON 저장: {OUT_DIR}")
    print(f"  이미지 저장: {IMG_DIR}")


if __name__ == "__main__":
    run()
