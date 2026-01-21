import sys
import os
import re
import traceback
import tkinter as tk

# -------------------------------------------------------------------------
# GUI 설정 창
# -------------------------------------------------------------------------
class ConfigDialog:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("한글 변환 설정")
        
        # 기본값
        self.merge_enabled = True   # 단독 자음 병합
        self.split_enabled = False  # 시작음 분리 (New!)
        self.sustain_enabled = True # + 변환
        
        window_width = 420
        window_height = 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        pos_x = int(screen_width / 2 - window_width / 2)
        pos_y = int(screen_height / 2 - window_height / 2)
        self.root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")

        # 1. 단독 자음(CVVC) 병합
        self.chk_merge_var = tk.BooleanVar(value=True)
        chk_merge = tk.Checkbutton(self.root, text="단독 자음 앞 노트 병합 (- C + CV)\n(예: [- n][na] -> [나][+] 또는 [나(길게)])", 
                             variable=self.chk_merge_var, justify="left")
        chk_merge.pack(pady=10, anchor="w", padx=20)

        # 2. 시작음 분리 옵션
        self.chk_split_var = tk.BooleanVar(value=False)
        chk_split = tk.Checkbutton(self.root, text="시작음(- CV) 분리 모드\n(예: [- na] -> [- n] + [나] 로 노트 쪼개기)\n(-n na 처럼 이미 적힌 경우도 분리 보존)", 
                             variable=self.chk_split_var, justify="left", fg="red")
        chk_split.pack(pady=5, anchor="w", padx=20)

        # 3. 모음 연속음 변환
        self.chk_sustain_var = tk.BooleanVar(value=True)
        chk_sustain = tk.Checkbutton(self.root, text="모음 연속음(VCV)을 + 로 변환\n(체크 해제 시: a a -> 아)", 
                             variable=self.chk_sustain_var, justify="left")
        chk_sustain.pack(pady=5, anchor="w", padx=20)

        # 안내 문구
        info_text = (
            "※ 변환 우선순위:\n"
            "1. 시작음 분리 (켜져 있을 시 최우선)\n"
            "2. 앞 노트 병합\n"
            "3. 일반 변환 (u n -> 운)"
        )
        lbl = tk.Label(self.root, text=info_text, fg="blue", justify="left")
        lbl.pack(pady=10, anchor="w", padx=22)

        # 실행 버튼
        btn = tk.Button(self.root, text="변환 시작", command=self.on_ok, width=20, height=2)
        btn.pack(pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def on_ok(self):
        self.merge_enabled = self.chk_merge_var.get()
        self.split_enabled = self.chk_split_var.get()
        self.sustain_enabled = self.chk_sustain_var.get()
        self.root.destroy()

    def on_cancel(self):
        self.root.destroy()
        sys.exit(0)

    def show(self):
        self.root.mainloop()
        return self.merge_enabled, self.split_enabled, self.sustain_enabled

# -------------------------------------------------------------------------
# 유틸리티 & 로깅
# -------------------------------------------------------------------------
def log(msg):
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except: pass

BASE_CODE = 0xAC00

MAP_CHO = {
    'kk': 1, 'gg': 1, 'g': 0, 'k': 15, 'n': 2, 'd': 3, 'tt': 4, 'dd': 4, 't': 16,
    'r': 5, 'l': 5, 'm': 6, 'b': 7, 'pp': 8, 'bb': 8, 'p': 17,
    'ss': 10, 's': 9, 'j': 12, 'jj': 13, 'ch': 14, 'c': 14,
    'z': 12, 'h': 18, '': 11
}
MAP_JUNG = {
    'yae': 3, 'yeo': 6, 'wae': 10, 'woe': 11, 'wuo': 14, 'we': 15, 'wi': 16, 'ui': 19,
    'a': 0, 'ae': 1, 'ya': 2, 'eo': 4, 'e': 5, 'ye': 7, 
    'o': 8, 'wa': 9, 'yo': 12, 'u': 13, 'woo': 13, 'wo': 14,
    'yu': 17, 'eu': 18, 'i': 20, 'y': 20
}
MAP_JONG = {
    '': 0, 'kk': 2, 'ks': 3, 'nc': 5, 'nh': 6, 'lk': 9, 'lm': 10, 'lb': 11, 'ls': 12, 'lt': 13, 'lp': 14, 'lh': 15, 'bs': 18, 'ss': 20, 'ng': 21,
    'g': 1, 'k': 1, 'n': 4, 'd': 7, 't': 7, 'r': 8, 'l': 8, 
    'm': 16, 'b': 17, 'p': 17, 's': 19, 'j': 22, 'ch': 23, 'z': 22, 'h': 27
}

def get_pure_syllable(text):
    """ 순수 알파벳만 추출 (소문자 변환) """
    return re.sub(r'[^a-zA-Z]', '', text).lower()

def is_consonant_only(text):
    """ 자음만 있는 노트인지 확인 (- n, k, n m 등) """
    clean = get_pure_syllable(text)
    if not clean: return False
    for vowel in MAP_JUNG.keys():
        if vowel in clean:
            return False
    return True

def is_vowel_sustain_text(lyric):
    """ 모음 연음 텍스트 패턴 확인 (o o, wa a) """
    clean_lyric = re.sub(r'[^a-zA-Z\s]', '', lyric).lower()
    parts = clean_lyric.split()
    if len(parts) < 2 or 'bre' in clean_lyric: return False
    prev, curr = parts[-2], parts[-1]
    if curr not in MAP_JUNG: return False
    if prev.endswith(curr): return True
    return False

def is_breath_alias(lyric):
    """ R/H 대문자 포함 여부 (숨소리) """
    if 'R' in lyric or 'H' in lyric: return True
    return False

def convert_syllable(text):
    if not text: return None
    cho_idx, jung_idx, jong_idx = -1, -1, 0
    
    sorted_cho = sorted(MAP_CHO.keys(), key=len, reverse=True)
    sorted_jung = sorted(MAP_JUNG.keys(), key=len, reverse=True)
    
    is_vowel_start = False
    for j in sorted_jung:
        if text.startswith(j):
            cho_idx = 11; is_vowel_start = True; break
            
    matched_cho_len = 0
    if not is_vowel_start:
        for c in sorted_cho:
            if c == '': continue
            if text.startswith(c):
                remain = text[len(c):]
                for j in sorted_jung:
                    if remain.startswith(j):
                        cho_idx = MAP_CHO[c]; matched_cho_len = len(c); break
                if cho_idx != -1: break
    
    if cho_idx == -1: return None
    text = text[matched_cho_len:]
    
    matched_jung_len = 0
    for j in sorted_jung:
        if text.startswith(j):
            jung_idx = MAP_JUNG[j]; matched_jung_len = len(j); break
    
    if jung_idx == -1: return None
    text = text[matched_jung_len:]
    
    if text in MAP_JONG: jong_idx = MAP_JONG[text]
    else: return None

    return chr(BASE_CODE + (cho_idx * 21 * 28) + (jung_idx * 28) + jong_idx)

def parse_romaji_smart(lyric):
    if 'bre' in lyric.lower(): return None
    if lyric == "+": return "+"

    parts = lyric.split()
    if len(parts) > 1:
        res = convert_syllable(get_pure_syllable(parts[-1]))
        if res: return res

    res = convert_syllable(get_pure_syllable(lyric))
    if res: return res
    
    return None

def try_merge_forward(consonant_part, next_part):
    c = get_pure_syllable(consonant_part)
    n_part_full = get_pure_syllable(next_part)
    
    if n_part_full.startswith(c):
        res = convert_syllable(n_part_full)
        if res: return res
    
    res = convert_syllable(c + n_part_full)
    if res: return res
    return None

def extract_start_consonant(lyric):
    """ '- na' -> 'n' 추출 """
    clean = get_pure_syllable(lyric)
    sorted_cho = sorted(MAP_CHO.keys(), key=len, reverse=True)
    for c in sorted_cho:
        if c == '': continue
        if clean.startswith(c):
            return c
    return None

class Note:
    def __init__(self, data_dict):
        self.data = data_dict
        self.lyric = data_dict.get('Lyric', '')
        self.length = int(data_dict.get('Length', 480))
        self.note_num = int(data_dict.get('NoteNum', 60))

    def to_string(self):
        lines = []
        lines.append(f"[#{self.data['id']}]")
        for k, v in self.data.items():
            if k == 'id': continue
            if k == 'Lyric': lines.append(f"Lyric={self.lyric}")
            elif k == 'Length': lines.append(f"Length={self.length}")
            elif k == 'NoteNum': lines.append(f"NoteNum={self.note_num}")
            else: lines.append(f"{k}={v}")
        return "\n".join(lines)
        
    def clone(self, new_id_suffix):
        new_data = self.data.copy()
        new_data['id'] = str(self.data['id']) + new_id_suffix
        return Note(new_data)

def main():
    try:
        if len(sys.argv) < 2: 
            ConfigDialog().show()
            return
        tmp_file = sys.argv[1]
        
        dialog = ConfigDialog()
        enable_merge_forward, enable_split_start, enable_sustain = dialog.show()
        
        notes = []
        current_note_data = {}
        
        try:
            with open(tmp_file, 'r', encoding='utf-8', errors='ignore') as f: lines = f.readlines()
        except:
             with open(tmp_file, 'r', encoding='cp949', errors='ignore') as f: lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if line.startswith('[#') and line.endswith(']'):
                if current_note_data: notes.append(Note(current_note_data))
                current_note_data = {'id': line[2:-1]}
            elif '=' in line:
                k, v = line.split('=', 1)
                current_note_data[k] = v
        if current_note_data: notes.append(Note(current_note_data))

        processed_notes = []
        
        i = 0
        while i < len(notes):
            curr = notes[i]
            
            # 1. 스킵 조건
            if len(curr.lyric) > 0 and (ord(curr.lyric[0]) >= 0xAC00 or is_breath_alias(curr.lyric) or 'bre' in curr.lyric.lower()):
                processed_notes.append(curr)
                i += 1
                continue

            # -----------------------------------------------------------
            # [NEW] 시작음 분리 로직 (수정됨: -n na 케이스 대응)
            # -----------------------------------------------------------
            if enable_split_start and curr.lyric.strip().startswith('-'):
                # 단독 자음(- n)이 아닌 경우만
                if not is_consonant_only(curr.lyric):
                    
                    target_cons = None
                    target_cv = None
                    
                    # [중요 수정] 가사 파싱 시도 (공백 기준 분리)
                    parts = curr.lyric.strip().split()
                    
                    # Case 1: "-n na" 처럼 자음이 명시적으로 분리된 경우
                    # (조건: 2덩어리 이상, 첫 덩어리가 '-'로 시작하고 길이가 1보다 큼)
                    if len(parts) >= 2 and parts[0].startswith('-') and len(parts[0]) > 1:
                        target_cons = get_pure_syllable(parts[0]) # -n -> n
                        target_cv = get_pure_syllable(parts[1])   # na -> na
                        
                    # Case 2: "- na" 또는 "-na" 처럼 뭉뚱그려진 경우 (기존 로직)
                    else:
                        clean_full = get_pure_syllable(curr.lyric)
                        target_cons = extract_start_consonant(clean_full)
                        target_cv = clean_full # 나중에 여기서 start_cons만큼 잘라낼 필요 없이 그냥 통째로 넣으면 됨 (어차피 parse_romaji가 처리)

                    # 분리 실행 (길이 체크 >= 10)
                    if target_cons and target_cv and curr.length >= 10:
                        
                        cons_len = min(60, int(curr.length / 2))
                        
                        if cons_len > 0:
                            # 1. 자음 노트 생성
                            note_cons = curr.clone("_split_c")
                            note_cons.lyric = f"- {target_cons}" 
                            note_cons.length = cons_len
                            
                            # 2. 모음(CV) 노트 수정
                            curr.length -= cons_len
                            curr.lyric = target_cv # "-n na"의 경우 "na", "-na"의 경우 "na"
                            
                            processed_notes.append(note_cons)
                            # curr는 루프 아래로 흘려보내서 "na" -> "나" 변환
                            
            # -----------------------------------------------------------

            # 3. 자음만 있는 노트 처리
            if is_consonant_only(curr.lyric):
                # Type A: Forward Merge
                if enable_merge_forward and curr.lyric.strip().startswith('-') and (i + 1 < len(notes)):
                    next_note = notes[i+1]
                    if 'bre' not in next_note.lyric.lower() and not is_breath_alias(next_note.lyric):
                        merged_hangul = try_merge_forward(curr.lyric, next_note.lyric)
                        if merged_hangul:
                            if curr.note_num == next_note.note_num: 
                                curr.lyric = merged_hangul     
                                curr.length += next_note.length 
                                processed_notes.append(curr)
                                i += 2 
                                continue
                            else: 
                                curr.lyric = merged_hangul     
                                next_note.lyric = "+"          
                                processed_notes.append(curr)
                                i += 1 
                                continue
                
                # Type B: Backward Merge
                if not curr.lyric.strip().startswith('-') and len(processed_notes) > 0:
                    prev_note = processed_notes[-1]
                    if curr.note_num == prev_note.note_num:
                        prev_note.length += curr.length
                        i += 1
                        continue
                    else:
                        curr.lyric = "+"
                        processed_notes.append(curr)
                        i += 1
                        continue
            
            # 4. 모음 연속음 (+) 처리
            if enable_sustain and is_vowel_sustain_text(curr.lyric):
                curr.lyric = "+"
                processed_notes.append(curr)
                i += 1
                continue

            # 5. 일반 변환
            converted = parse_romaji_smart(curr.lyric)
            if converted:
                curr.lyric = converted
            
            processed_notes.append(curr)
            i += 1

        with open(tmp_file, 'w', encoding='utf-8-sig') as f:
            for note in processed_notes:
                f.write(note.to_string() + "\n")
        
    except Exception as e:
        log(traceback.format_exc())

if __name__ == '__main__':
    main()