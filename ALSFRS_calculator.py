import re
import unicodedata
import streamlit as st

st.set_page_config(page_title="Calculadora ALSFRS-R", layout="wide")

# =========================================================
# GLOBAL STYLES (mesmo estilo do seu template)
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
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _norm(s: str) -> str:
    return _strip_accents((s or "").strip().lower())

def inline_label_radio(label_text: str, options, format_func, key: str, index=None):
    c_label, c_radio, _fill = st.columns([3.2, 6.0, 10.0], vertical_alignment="top")
    with c_label:
        st.markdown(f'<div class="inline-label">{label_text}</div>', unsafe_allow_html=True)
    with c_radio:
        return st.radio(
            "",
            options=options,
            format_func=format_func,
            index=index,
            key=key,
            label_visibility="collapsed",
        )

def _all_item_keys():
    return [f"als_{i}" for i in [1,2,3,4,5,6,7,8,9,10,11,12]] + ["als_5_mode", "als_import_text"]

def _reset_alsfrs():
    for k in _all_item_keys():
        st.session_state.pop(k, None)

# =========================================================
# ALSFRS-R OPTION TEXTS (do PDF)
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
    7: ("Cama", {
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
    12: ("IResp", {
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
    5:"Alimentação", 6:"Vestuário", 7:"Cama", 8:"Andar",
    9:"Escadas", 10:"Dispneia", 11:"Ortopneia", 12:"IResp"
}

# =========================================================
# EXPORT
# =========================================================
def get_item5_mode() -> str:
    mode = st.session_state.get("als_5_mode", "5a")
    return mode if mode in ("5a", "5b") else "5a"

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

    # Nome do item 5 depende do modo
    item5_label = "Alimentação" if mode5 == "5a" else "GTT"

    parts = []
    for i in ORDER:
        if i == 5:
            parts.append(f"{item5_label}.{vals[i]}")
        else:
            parts.append(f"{LABELS_FOR_OUTPUT[i]}.{vals[i]}")

    out = f"ALSFRS: {total} = " + " / ".join(parts)
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
    7: ["cama", "virar", "lencol", "lençol"],
    8: ["andar", "marcha", "deambul"],
    9: ["escad", "subir"],
    10: ["dispne", "falta de ar"],
    11: ["ortopne", "travesseir"],
    12: ["iresp", "insuf", "bipap", "ventil"],
}

def _try_parse_numbered_tokens(text: str):
    """
    Formato tipo:
      "1.4 / 2.3 / ... / 5a.2 / ... / 12.4"
    """
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

    # precisa ter ao menos 10 para ser considerado esse formato
    if len(got) < 10:
        return None

    # completa por ordem se estiver faltando algo (raro), mas só aceita se ficar 12
    if not all(i in got for i in ORDER):
        return None

    return got, (mode5 or get_item5_mode())

def _try_parse_scores_only(text: str):
    """
    Formato:
      "ALSFRS: 35 = 4 / 3 / 3 / 2 / 2 / 3 / 3 / 2 / 1 / 4 / 4 / 4"
    """
    t = text or ""
    # remove cabeçalho com total, se houver
    t2 = re.sub(r"(?i)alsfrs\s*:\s*\d+\s*=", "", t).strip()

    scores = re.findall(r"\b([0-4])\b", t2)
    if len(scores) != 12:
        return None

    got = {i: int(scores[idx]) for idx, i in enumerate(ORDER)}
    return got, get_item5_mode()

def _try_parse_labeled(text: str):
    """
    Formato:
      "ALSFRS: 35 = Fala.4 / Salivação.3 / ... / IResp.4"
    """
    t = text or ""
    if "/" not in t and "alsfrs" not in _norm(t):
        return None

    # modo do item 5 (se aparecer "gtt" ou "5b", assume 5b)
    n = _norm(t)
    mode5 = "5b" if ("gtt" in n or "5b" in n or "gastrost" in n) else "5a"

    got = {}
    parts = [p.strip() for p in t.split("/") if p.strip()]
    for p in parts:
        pn = _norm(p)

        # score = último dígito 0-4 no final do pedaço
        mm = re.search(r"([0-4])\s*$", p.strip())
        if not mm:
            continue
        score = int(mm.group(1))

        # acha qual item é pelo label
        for i in ORDER:
            for syn in LABEL_SYNONYMS[i]:
                if syn in pn:
                    got[i] = score
                    break
            if i in got:
                break

        # item 5: forçar modo se reconhecer "gtt"
        if 5 in got:
            if "gtt" in pn or "5b" in pn or "gastrost" in pn:
                mode5 = "5b"
            elif "aliment" in pn or "5a" in pn:
                mode5 = "5a"

    if len(got) != 12:
        return None

    return got, mode5

def parse_alsfrs_import(text: str):
    text = (text or "").strip()
    if not text:
        return False, "Cole um texto para importar.", None

    parsed = _try_parse_numbered_tokens(text)
    if parsed is None:
        parsed = _try_parse_labeled(text)
    if parsed is None:
        parsed = _try_parse_scores_only(text)

    if parsed is None:
        return (
            False,
            "Não foi possível reconhecer o formato. Use um dos 3 formatos suportados (com labels, só números, ou '1.4/2.3/.../12.4').",
            None,
        )

    got, mode5 = parsed

    # valida
    for i in ORDER:
        if i not in got:
            return False, "Importação incompleta (faltam itens).", None
        if got[i] < 0 or got[i] > 4:
            return False, "Importação inválida: valores devem ser 0–4.", None

    return True, "Importação concluída.", (got, mode5)

def apply_import(got: dict, mode5: str):
    st.session_state["als_5_mode"] = mode5
    for i in ORDER:
        st.session_state[f"als_{i}"] = int(got[i])

# =========================================================
# IMPORT TRIGGER (antes da UI)
# =========================================================
if st.session_state.get("_do_als_import", False):
    st.session_state["_do_als_import"] = False
    ok, msg, payload = parse_alsfrs_import(st.session_state.get("_als_import_raw", ""))
    if ok and payload:
        got, mode5 = payload
        apply_import(got, mode5)
    st.session_state["_als_import_result"] = (ok, msg)
    st.rerun()

# =========================================================
# UI
# =========================================================
st.title("Calculadora ALSFRS-R")
st.markdown(
    "<div style='font-size:22px; color:#666; margin-top:-0.5rem; margin-bottom:1rem;'>"
    "seleção de 0–4 por item (12 itens) + export/import"
    "</div>",
    unsafe_allow_html=True,
)

# Item 5 mode
st.subheader("Configuração do item 5 (Alimentação vs GTT)")
mode5 = st.radio(
    "",
    options=["Sem gastrostomia (5a → Alimentação)", "Com gastrostomia (5b → GTT)"],
    index=0 if get_item5_mode() == "5a" else 1,
    key="_als5_mode_ui",
)
st.session_state["als_5_mode"] = "5a" if mode5.startswith("Sem") else "5b"

st.divider()
st.subheader("Itens da escala")

def render_item(item_number: int):
    key = f"als_{item_number}"
    current = st.session_state.get(key, None)
    idx = None
    if current is not None:
        try:
            idx = [4,3,2,1,0].index(int(current))
        except Exception:
            idx = None

    if item_number == 5:
        m = get_item5_mode()
        label, opts = ALSFRS_ITEMS[m]
        inline_label_radio(
            f"5. {label}",
            options=[4,3,2,1,0],
            format_func=lambda v: opts[v],
            key=key,
            index=idx,
        )
        return

    label, opts = ALSFRS_ITEMS[item_number]
    inline_label_radio(
        f"{item_number}. {label}",
        options=[4,3,2,1,0],
        format_func=lambda v: opts[v],
        key=key,
        index=idx,
    )

# layout em duas colunas
cA, cB = st.columns(2, vertical_alignment="top")
with cA:
    for i in [1,2,3,4,5,6]:
        render_item(i)
with cB:
    for i in [7,8,9,10,11,12]:
        render_item(i)

st.divider()
st.subheader("Resultado")

ok, out = build_alsfrs_output()
if ok:
    st.success("Escala calculada.")
    st.text_area("Copiar resultado", value=out, height=90)
else:
    st.info(out)
    st.text_area("Copiar resultado", value="", height=90, placeholder="Preencha todos os itens para gerar o texto final.")

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
    "Cole aqui um resultado prévio (qualquer um dos 3 formatos suportados)",
    key="als_import_text",
    height=120,
    placeholder=(
        "Ex. 1 (com labels): ALSFRS: 35 = Fala.4 / Salivação.3 / ... / IResp.4\n"
        "Ex. 2 (só números): ALSFRS: 35 = 4 / 3 / 3 / 2 / 2 / 3 / 3 / 2 / 1 / 4 / 4 / 4\n"
        "Ex. 3 (numerado): ALSFRS: 35 = 1.4 / 2.3 / 3.3 / 4.2 / 5a.2 / 6.3 / 7.3 / 8.2 / 9.1 / 10.4 / 11.4 / 12.4"
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

