from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from datetime import date, datetime
import hashlib, re
from typing import Optional, Dict, List

app = FastAPI(title="seed-mini-writer", version="1.0.0")

TYPE6_LABEL = ["サイレンス(静)","ブースト(動)","インナー(内)","アウター(外)","ロジカ(理)","エモティブ(情)"]
SEASON_WORDS = {1:"冬",2:"冬",3:"春",4:"春",5:"初夏",6:"夏",7:"夏",8:"晩夏",9:"秋",10:"秋",11:"初冬",12:"冬"}

class NameDOBInput(BaseModel):
    name_kanji: str
    name_kana: str
    dob: str
    old_form: bool = False
    romanization: Optional[str] = "hepburn"
    today: Optional[str] = None
    mode: str = "both"
    @validator("name_kana")
    def only_hiragana(cls, v):
        if not re.fullmatch(r"[ぁ-ゖーっ]+(?:\s*[ぁ-ゖーっ]+)*", v):
            raise ValueError("ふりがなは ひらがな/長音/促音 のみ")
        return v
    @validator("dob")
    def valid_date(cls, v):
        d = date.fromisoformat(v); 
        if d < date(1900,1,1) or d > date.today(): raise ValueError("1900-01-01〜今日の範囲")
        return v

def day_seed(name_kana: str, dob: str, today_str: Optional[str]) -> str:
    if today_str is None: today_str = date.today().isoformat()
    return hashlib.sha256(f"{name_kana}|{dob}|{today_str}".encode()).hexdigest()

def mora_like_count(kana: str) -> int:
    return len(re.findall(r"[ぁ-ゖーっ]", kana))

def sum_digits_yyyymmdd(dob: str) -> int:
    return sum(int(c) for c in re.sub(r"\D","",dob))

def decide_type6(kana: str, dob: str) -> int:
    return (mora_like_count(kana) + sum_digits_yyyymmdd(dob)) % 6

def clamp40(s: str) -> str:
    n=len(s)
    while n<38: s+="。"; n=len(s)
    return s[:42] if n>42 else s

TEMPLATES = {
  0: {"name_only":["静かな整え時。余白を保ち、一歩を小さく。"],
      "merged":["{season}の光に合わせて整える。静かに輪郭を揃える。"]},
  1: {"name_only":["勢いで空気を変える。小さく速く踏み出す。"],
      "merged":["{season}の熱で背中を押す。まず一歩、短く速く。"]},
  2: {"name_only":["核を温め直す。独りの時間で底を厚く。"],
      "merged":["静かな{season}。核を練り、深く積む。"]},
  3: {"name_only":["窓を開ける。短く届く言葉で触れる。"],
      "merged":["{season}の風に乗せて一言。接点が道になる。"]},
  4: {"name_only":["枠を引く。順序を整え、無駄を削る。"],
      "merged":["{season}に構造を敷く。要点三つで進路を描く。"]},
  5: {"name_only":["共感を灯す。好き一粒から育てる。"],
      "merged":["やわらかな{season}。温度を燃料に進む。"]}
}

@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.utcnow().isoformat()+"Z"}

class ValidateDateIn(BaseModel):
    text: str

@app.post("/v1/generate")
def generate(p: NameDOBInput):
    seed = day_seed(p.name_kana, p.dob, p.today)
    idx = decide_type6(p.name_kana, p.dob)
    month = int(p.dob[5:7]); season = SEASON_WORDS.get(month,"季節")
    out: Dict[str,str] = {"type6_index": idx, "type6_label": TYPE6_LABEL[idx], "seed": seed, "season": season}

    name_only = clamp40(TEMPLATES[idx]["name_only"][0])
    merged = clamp40(TEMPLATES[idx]["merged"][0].format(season=season) + ("（旧字体）" if p.old_form else ""))
    if p.mode in ("name_only","both"): out["name_only_40"] = name_only
    if p.mode in ("merged","both"): out["merged_40"] = merged
    return {"ok": True, "data": out}
