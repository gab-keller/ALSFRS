import re
import unicodedata
from datetime import date
import streamlit as st

st.set_page_config(page_title="Calculadora ALSFRS-R", layout="wide")

# =========================================================
# GLOBAL STYLES
# =========================================================
st.markdown(
    """
    <style>
      section.main > div.block-container{
        max-width: 100% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
      }

      /* Make all subheader titles (st.subheader) red */
      h3 { color: #c00000 !important; }
      h3 strong { color: #c00000 !important; }

      /* Inline label look */
      .inline-label{
        font-size: 0.95rem;
        color: #333;
        padding-top: 0.35rem;
        white-space: nowrap;
        word-break: normal;
        overflow-wrap: normal;
      }

      /* GLOBAL VERTICAL SPACING TIGHTENER */
      div[data-testid="stMarkdown"] p,
      div[data-testid="stMarkdown"] h1,
      div[data-testid="stMarkdown"] h2,
      div[data-testid="stMarkdown"] h3,
      div[data-testid="stMarkdown"] h4,
      div[data-testid="stMarkdown"] h5,
      div[data-testid="stMarkdown"] h6 {
        margin-bottom: 0.15rem !important;
        margin-top: 0.15rem !important;
      }

      div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {
        margin-bottom: 0.35rem !important;
      }

      div[data-testid="stTextArea"],
      div[data-testid="stRadio"],
      div[data-testid="stCheckbox"],
      div[data-testid="stTextInput"],
      div[data-testid="stSelectbox"] {
        margin-top: -0.35rem !important;
      }

      label, .stTextArea label, .stRadio label, .stCheckbox label {
        margin-bottom: 0.15rem !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================
def _strip_accents(s: str) -> str:
    s = s or ""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )

def _norm(s: str) -> str:
    return _strip_accents((s or "").strip().lower())

def inline_label_radio(
    label_text: str,
    options,
    format_func,
    key: str,
    *,
    index_if_missing=None,
):
    """
    Avoid Streamlit warning:
    "widget with key ... was created with a default value but also had its value set via the Session State API"
    => only pass 'index' when the key is NOT already in st.session_state.
    """
    c_label, c_radio, _fill = st.columns([3.2, 6.0, 10.0], vertical_alignment="top")
    with c_label:
        st.markdown(
            f'<div class="inline-label">{label_text}</div>', unsafe_allow_html=True
        )
    with c_radio:
        kwargs = dict(
            options=options,
            format_func=format_func,
            key=key,
            label_visibility="collapsed",
        )
        if key not in st.session_state:
            kwargs["index"] = index_if_missing  # can be None to allow "no selection"
        return st.radio("", **kwargs)

def _all_item_keys():
    return (
        [f"als_{i}" for i in [1,2,3,4,5,6,7,8,9,10,11,12]]
        + ["als_5_mode", "als_import_text", "als_date_mm_yyyy"]
    )

def _reset_alsfrs():
    for k in _all_item_keys():
        st.session_state.pop(k, None)

def _fmt_mm_yyyy(mm: int, yyyy: int) -> str:
    mm = int(mm)
    yyyy = int(yyyy)
    mm = max(1, min(12, mm))
    if yyyy < 1900:
        yyyy = 1900
    return f"{mm:02d}/{yyyy:04d}"

def _default_mm_yyyy() -> str:
    today = date.today()
    return f"{today.month:02d}/{today.year:04d}"

def _parse_mm_yyyy(s: str) -> str | None:
    """
    Accepts:
      - MM/YYYY
      - M/YYYY
      - MM-YYYY
      - MM.YYYY
    Returns standardized MM/YYYY or None if invalid.
    """
    s = (s or "").strip()
    m = re.match(r"^\s*(\d{1,2})\s*[/\-.]\s*(\d{4})\s*$", s)
    if not m:
        return None
    mm = int(m.group(1))
    yyyy = int(m.group(2))
    if not (1 <= mm <= 12):
        return None
    if not (1900 <= yyyy <= 2100):
        return None
    return _fmt_mm_yyyy(mm, yyyy)

# =========================================================
# ALSFRS-R OPTION TEXTS
# =========================================================
ALSFRS_ITEMS = {
    1: ("Fala", {
        4: "4. Normal",
        3: "3. Distúrbio da fala detectável",
        2: "2. Compreensível com repetição",
        1: "1. Fala combinada com comunicação não-vocal",
        0: "0. Perda de fala funcional",
    }),
    2: ("Salivação", {
        4: "4. Normal",
        3: "3. Excesso leve de saliva na boca, podendo ter babação noturna",
        2: "2. Excesso moderado de saliva, podendo ter mínima babação diurna",
        1: "1. Excesso acentuado de saliva com alguma baba",
        0: "0. Babação acentuada exigindo constante uso de babador ou lenço para boca",
    }),
    3: ("Deglutição", {
        4: "4. Normal",
        3: "3. Problemas iniciais para comer, engasgos ocasionais",
        2: "2. Alteração na consistência da dieta",
        1: "1. Necessidade de suplemento alimentar por tubo de alimentação",
        0: "0. Exclusivamente enteral ou parenteral",
    }),
    4: ("Escrita", {
        4: "4. Normal",
        3: "3. Lentificada ou descuidada, todas as palavras são legíveis",
        2: "2. Nem todas as palavras são legíveis",
        1: "1. Capaz de segurar a caneta, mas incapaz de escrever",
        0: "0. Não é capaz de segurar a caneta",
    }),
    # Item 5 é especial (5a ou 5b)
    "5a": ("Alimentação", {  # sem gastrostomia
        4: "4. Normal",
        3: "3. Um pouco lento e desajeitado, mas não necessita de ajuda",
        2: "2. Necessita de alguma ajuda",
        1: "1. Alimentos cortados por outra pessoa, mas alimenta-se sozinho lentamente",
        0: "0. Precisa ser alimentado",
    }),
    "5b": ("GTT", {  # com gastrostomia
        4: "4. Normal",
        3: "3. Desajeitado, mas capaz de desempenhar todas as manipulações",
        2: "2. Alguma ajuda necessária com tampas e fechos",
        1: "1. Oferece assistência mínima ao cuidador",
        0: "0. Incapaz de executar qualquer aspecto da tarefa",
    }),
    6: ("Vestuário", {
        4: "4. Normal",
        3: "3. Independente e realiza completamente o autocuidado com esforço e menor eficiência",
        2: "2. Assistência intermitente ou substituição dos métodos",
        1: "1. Necessita do cuidador para autocuidado",
        0: "0. Dependência total",
    }),
    7: ("Lençol", {
        4: "4. Normal",
        3: "3. Consegue lento e desajeitado, mas sem ajuda",
        2: "2. Pode se transferir sozinho e ajustar o lençol, mas com grande dificuldade",
        1: "1. Pode iniciar, mas não se transfere ou ajusta o lençol sozinho",
        0: "0. Dependência total",
    }),
    8: ("Andar", {
        4: "4. Normal",
        3: "3. Dificuldades iniciais na deambulação",
        2: "2. Anda com assistência",
        1: "1. Movimento funcional não-deambulatório somente",
        0: "0. Não apresenta movimentação voluntária das pernas",
    }),
    9: ("Escadas", {
        4: "4. Normal",
        3: "3. Lento",
        2: "2. Algum desequilíbrio ou fadiga",
        1: "1. Necessita de assistência",
        0: "0. Não realiza",
    }),
    10: ("Dispneia", {
        4: "4. Nenhuma",
        3: "3. Ocorre quando caminha",
        2: "2. Ocorre quando come, toma banho e se veste",
        1: "1. Ocorre no repouso, tanto sentado quanto deitado",
        0: "0. Dificuldade significativa, considerando suporte mecânico",
    }),
    11: ("Ortopneia", {
        4: "4. Nenhuma",
        3: "3. Alguma dificuldade de dormir devido falta de ar; não se utiliza rotineiramente mais que 2 travesseiros",
        2: "2. Necessita de travesseiros extras para dormir (mais que 2)",
        1: "1. Pode dormir somente sentado",
        0: "0. Não consegue dormir",
    }),
    12: ("Insuficiência respiratória", {
        4: "4. Nenhuma",
        3: "3. Uso intermitente do BIPAP",
        2: "2. Uso contínuo do BIPAP à noite",
        1: "1. Uso contínuo do BIPAP durante o dia e a noite",
        0: "0. Ventilação mecânica invasiva por intubação",
    }),
}

ORDER = [1,2,3,4,5,6,7,8,9,10,11,12]
LABELS_FOR_OUTPUT = {
    1:"Fala", 2:"Salivação", 3:"Deglutição", 4:"Escrita",
    5:"Alimentação", 6:"Vestuário",
    7:"Lençol",
    8:"Andar", 9:"Escadas", 10:"Dispneia", 11:"Ortopneia", 12:"IResp"
}

# =========================================================
# EXPORT
# =========================================================
def get_item5_mode() -> str:
    mode = st.session_state.get("als_5_mode", "5a")
    return mode if mode in ("5a", "5b") else "5a"

def get_mm_yyyy() -> str:
    # if empty/invalid, fallback to current month/year
    raw = (st.session_state.get("als_date_mm_yyyy") or "").strip()
    parsed = _parse_mm_yyyy(raw)
    return parsed if parsed else _default_mm_yyyy()

def build_alsfrs_output() -> tuple[bool, str]:
    mode5 = get_item5_mode()

    vals = {}
    for i in ORDER:
        k = f"als_{i}"
        v = st.session_state.get(k, None)
        if v is None:
            return (False, "Preencha todos os 12 itens para gerar o resultado.")
        try:
            iv = int(v)
        except Exception:
            return (False, "Há um ou mais itens com valor inválido.")
        if iv < 0 or iv > 4:
            return (False, "Há um ou mais itens fora do intervalo 0–4.")
        vals[i] = iv

    total = sum(vals.values())

    item5_label = "Alimentação" if mode5 == "5a" else "GTT"

    parts = []
    for i in ORDER:
        if i == 5:
            parts.append(f"{item5_label}.{vals[i]}")
        else:
            parts.append(f"{LABELS_FOR_OUTPUT[i]}.{vals[i]}")

    mm_yyyy = get_mm_yyyy()
    out = f"ALSFRS ({mm_yyyy}): " + " / ".join(parts) + f" = {total}"
    return (True, out)

# =========================================================
# IMPORT PARSER
# =========================================================
LABEL_SYNONYMS = {
    1: ["fala"],
    2: ["saliv", "saliva"],
    3: ["deglut", "degluti"],
    4: ["escrita"],
    5: ["aliment", "utens", "gtt", "gastro", "gastrost"],
    6: ["vestu", "higien"],
    7: ["lencol", "cama", "virar"],
    8: ["andar", "marcha", "deambul"],
    9: ["escad", "subir"],
    10: ["dispne", "falta de ar"],
    11: ["ortopne", "travesseir"],
    12: ["iresp", "insuf", "bipap", "ventil"],
}

def _try_parse_numbered_tokens(text: str):
    t = text or ""
    patt = re.compile(r"(?i)\b(5a|5b|10|11|12|[1-9])\s*[.:]\s*([0-4])\b")
    matches = list(patt.finditer(t))
    if not matches:
        return None

    got = {}
    mode5 = None
    for m in matches:
        iid = m.group(1).lower()
        score = int(m.group(2))
        if iid in ("5a", "5b"):
            got[5] = score
            mode5 = iid
        else:
            got[int(iid)] = score

    if not all(i in got for i in ORDER):
        return None

    return got, (mode5 or get_item5_mode())

def _try_parse_scores_only(text: str):
    t = text or ""
    t2 = re.sub(r"(?i)alsfrs\s*(\(\s*\d{1,2}\s*[/\-.]\s*\d{4}\s*\))?\s*:\s*", "", t).strip()
    t2 = re.sub(r"\s*=\s*\d+\s*$", "", t2).strip()
    scores = re.findall(r"\b([0-4])\b", t2)
    if len(scores) != 12:
        return None
    got = {i: int(scores[idx]) for idx, i in enumerate(ORDER)}
    return got, get_item5_mode()

def _try_parse_labeled(text: str):
    t = text or ""
    if "/" not in t and "alsfrs" not in _norm(t):
        return None

    n = _norm(t)
    mode5 = "5b" if ("gtt" in n or "5b" in n or "gastrost" in n) else "5a"

    got = {}
    parts = [p.strip() for p in t.split("/") if p.strip()]
    for p in parts:
        pn = _norm(p)
        mm = re.search(r"([0-4])\s*$", p.strip())
        if not mm:
            continue
        score = int(mm.group(1))

        for i in ORDER:
            for syn in LABEL_SYNONYMS[i]:
                if syn in pn:
                    got[i] = score
                    break
            if i in got:
                break

        if 5 in got:
            if "gtt" in pn or "5b" in pn or "gastrost" in pn:
                mode5 = "5b"
            elif "aliment" in pn or "5a" in pn:
                mode5 = "5a"

    if len(got) != 12:
        return None

    return got, mode5

def _extract_date_mm_yyyy(text: str) -> str | None:
    # ALSFRS (02/2026): ...
    m = re.search(r"(?i)alsfrs\s*\(\s*(\d{1,2}\s*[/\-.]\s*\d{4})\s*\)\s*:", text or "")
    if not m:
        return None
    return _parse_mm_yyyy(m.group(1))

def parse_alsfrs_import(text: str):
    text = (text or "").strip()
    if not text:
        return False, "Cole um texto para importar.", None

    parsed_date = _extract_date_mm_yyyy(text)

    parsed = _try_parse_numbered_tokens(text)
    if parsed is None:
        parsed = _try_parse_labeled(text)
    if parsed is None:
        parsed = _try_parse_scores_only(text)

    if parsed is None:
        return (
            False,
            "Não foi possível reconhecer o formato. Use um dos formatos suportados (com labels, só números, ou '1.4/2.3/.../12.4').",
            None,
        )

    got, mode5 = parsed

    for i in ORDER:
        if i not in got:
            return False, "Importação incompleta (faltam itens).", None
        if got[i] < 0 or got[i] > 4:
            return False, "Importação inválida: valores devem ser 0–4.", None

    return True, "Importação concluída.", (got, mode5, parsed_date)

def apply_import(got: dict, mode5: str, mm_yyyy: str | None):
    st.session_state["als_5_mode"] = mode5
    for i in ORDER:
        st.session_state[f"als_{i}"] = int(got[i])
    if mm_yyyy:
        st.session_state["als_date_mm_yyyy"] = mm_yyyy

# =========================================================
# IMPORT TRIGGER (antes da UI)
# =========================================================
if st.session_state.get("_do_als_import", False):
    st.session_state["_do_als_import"] = False
    ok, msg, payload = parse_alsfrs_import(st.session_state.get("_als_import_raw", ""))
    if ok and payload:
        got, mode5, mm_yyyy = payload
        apply_import(got, mode5, mm_yyyy)
    st.session_state["_als_import_result"] = (ok, msg)
    st.rerun()

# =========================================================
# UI
# =========================================================
st.title("Calculadora ALSFRS-R")
st.markdown(
    "<div style='font-size:22px; color:#666; margin-top:-0.5rem; margin-bottom:1rem;'>"
    "Cálculo automatizado da escala ALSFRS-R"
    "</div>",
    unsafe_allow_html=True,
)

st.session_state.setdefault("als_5_mode", "5a")
st.session_state.setdefault("als_date_mm_yyyy", _default_mm_yyyy())

# Date selector (MM/YYYY)
st.subheader("Data (mês/ano)")
st.text_input(
    "Mês/Ano (MM/AAAA)",
    key="als_date_mm_yyyy",
    placeholder=_default_mm_yyyy(),
    help="Formato: MM/AAAA (ex.: 02/2026). Se inválido ou vazio, usa o mês/ano atual.",
)

def render_item(item_number: int):
    key = f"als_{item_number}"

    if item_number == 5:
        mode5 = get_item5_mode()
        label5, opts5 = ALSFRS_ITEMS[mode5]
        inline_label_radio(
            f"5{'a' if mode5=='5a' else 'b'}. {label5}",
            options=[4, 3, 2, 1, 0],
            format_func=lambda v: opts5[v],
            key=key,
            index_if_missing=None,
        )
        return

    label, opts = ALSFRS_ITEMS[item_number]
    inline_label_radio(
        f"{item_number}. {label}",
        options=[4, 3, 2, 1, 0],
        format_func=lambda v: opts[v],
        key=key,
        index_if_missing=None,
    )

# -------------------------
# SCALE (single column) + separator line after each item
# -------------------------
st.subheader("Itens da escala")

for i in ORDER:
    if i == 5:
        st.markdown("**Selecione 5a ou 5b**")
        inline_label_radio(
            "Gastrostomia (GTT)",
            options=["5a", "5b"],
            format_func=lambda v: "Sem gastrostomia (5a)" if v == "5a" else "Com gastrostomia (5b)",
            key="als_5_mode",
            index_if_missing=None,
        )
        st.markdown("---")

    render_item(i)

    if i != ORDER[-1]:
        st.divider()

st.divider()
st.subheader("Resultado")

ok, out = build_alsfrs_output()
if ok:
    st.text_area("Copiar resultado", value=out, height=90)
else:
    st.info(out)
    st.text_area(
        "Copiar resultado",
        value="",
        height=90,
        placeholder="Preencha todos os itens para gerar o texto final.",
    )

b1, b2, _fill = st.columns([1.6, 1.2, 10.0], vertical_alignment="center")
with b1:
    if st.button("Limpar escala", type="secondary"):
        _reset_alsfrs()
        st.rerun()
with b2:
    if st.button("Recalcular", type="primary"):
        st.rerun()

# =========================================================
# IMPORT SECTION
# =========================================================
st.markdown("---")
st.subheader("Importar resultado prévio")

st.text_area(
    "Cole aqui um resultado prévio (formatos antigos ou o novo com data)",
    key="als_import_text",
    height=140,
    placeholder=(
        "Novo formato: ALSFRS (02/2026): Fala.3 / Salivação.2 / ... / IResp.4 = 42\n"
        "Formato antigo (labels): ALSFRS: 35 = Fala.4 / Salivação.3 / ... / IResp.4\n"
        "Formato antigo (só números): ALSFRS: 35 = 4 / 3 / 3 / 2 / 2 / 3 / 3 / 2 / 1 / 4 / 4 / 4\n"
        "Formato antigo (numerado): ALSFRS: 35 = 1.4 / 2.3 / ... / 12.4"
    ),
)

ci1, ci2, _ = st.columns([1.8, 1.4, 10.0], vertical_alignment="center")

def _request_als_import():
    st.session_state["_als_import_raw"] = st.session_state.get("als_import_text", "")
    st.session_state["_do_als_import"] = True

with ci1:
    st.button("Importar", key="btn_als_import", on_click=_request_als_import, type="primary")

with ci2:
    def _clear_import_box():
        st.session_state["als_import_text"] = ""
    st.button("Limpar texto colado", key="btn_als_clear_import", on_click=_clear_import_box)

res = st.session_state.get("_als_import_result")
if res:
    ok_msg, msg = res
    if ok_msg:
        st.success(msg)
    else:
        st.error(msg)
    st.session_state.pop("_als_import_result", None)
