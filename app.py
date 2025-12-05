import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import StringIO
import re
from datetime import datetime

st.set_page_config(page_title="Order XML → CSV", page_icon="📦", layout="wide")

st.title("📦 Order XML → Tabela de Pedidos")
st.markdown(
    """
Envie os **XMLs de pedido** (formato Arezzo) e o app irá:

- Ler o cabeçalho e os itens de cada pedido
- Converter para uma tabela consolidada
- Permitir download em **CSV** para você usar no seu fluxo de acompanhamento
"""
)

STATUS_MAP = {
    "0": "Cadastrado",
    "1": "Alterado",
    "2": "Cancelado",
}


def parse_to_date(raw: str) -> str:
    """Normalize different date formats into YYYY-MM-DD strings for Excel."""
    if not raw:
        return ""
    raw = raw.strip()

    # Pattern like TO_DATE('03102025','DDMMYYYY')
    m = re.search(r"TO_DATE\('(\d{8})','DDMMYYYY'\)", raw)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%d%m%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return ""

    # Plain numeric YYYYMMDD (e.g. 20251001)
    if re.fullmatch(r"\d{8}", raw):
        try:
            dt = datetime.strptime(raw, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Already a more "normal" date string: try some patterns
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback: return original string (as-is)
    return raw


def parse_arezzo_xml(file) -> pd.DataFrame:
    """Parse a single Arezzo PO XML into an item-level DataFrame."""
    try:
        tree = ET.parse(file)
    except ET.ParseError:
        return pd.DataFrame()

    root = tree.getroot()

    # --- Header (Pedido_Compra) ---
    header_access = root.find(".//STATEMENT_PEDIDO_COMPRA/Pedido_Compra/access")
    if header_access is None:
        return pd.DataFrame()

    header = {elem.tag: (elem.text or "").strip() for elem in header_access}

    dt_emissao_norm = parse_to_date(header.get("DT_EMISSAO", ""))

    # --- Items (Item_Pedido_Compra/access) ---
    items_section = root.find(".//STATEMENT_ITEM_PEDIDO_COMPRA/Item_Pedido_Compra")
    if items_section is None:
        return pd.DataFrame()

    rows = []
    for access in items_section.findall("access"):
        row_raw = {elem.tag: (elem.text or "").strip() for elem in access}

        # Basic fields
        pedido = header.get("NUM_PEDD_COMPRA", "")
        fornecedor = header.get("PESSOA_FORNECEDOR", "")
        marca_ido = header.get("MARCA_IDO", "")

        cd_item_compra = row_raw.get("CD_ITEM_COMPRA", "")
        material = row_raw.get("CD_ITEM_MATERIAL", "")
        desc_produto = row_raw.get("DESC_PRODUTO", "")
        linha_id = row_raw.get("ID_LINHA", "")
        linha_desc = row_raw.get("DESC_LINHA", "")
        modelo_id = row_raw.get("ID_MODELO", "")
        modelo_desc = row_raw.get("DESC_MODELO", "")
        colecao = row_raw.get("CD_COLECAO", "")
        estacao = row_raw.get("CD_ESTACAO", "")
        grade = row_raw.get("GRADE", "")

        # Quantidade
        quantidade_str = row_raw.get("TL_REQU", "0")
        try:
            quantidade = float(quantidade_str)
        except ValueError:
            quantidade = None

        # Status mapeado (só texto)
        status_codigo = row_raw.get("STATUS_ITEM_PEDD", "")
        status_texto = STATUS_MAP.get(status_codigo, status_codigo)

        # Cor: tudo depois do "|"
        cor = ""
        if "|" in desc_produto:
            parts = desc_produto.split("|")
            cor = parts[-1].strip()

        # Datas programadas
        dt_prog_entr = parse_to_date(row_raw.get("DT_PROG_ENTR", ""))
        dt_plan_entr_de = parse_to_date(row_raw.get("DT_PLAN_ENTR_DE", ""))
        dt_plan_entr_ate = parse_to_date(row_raw.get("DT_PLAN_ENTR_ATE", ""))

        row = {
            "pedido": pedido,
            "fornecedor": fornecedor,
            "marca_ido": marca_ido,
            "item_compra": cd_item_compra,
            "material": material,
            "descricao_produto": desc_produto,
            "cor": cor,
            "linha_id": linha_id,
            "linha_desc": linha_desc,
            "modelo_id": modelo_id,
            "modelo_desc": modelo_desc,
            "colecao": colecao,
            "estacao": estacao,
            "grade": grade,
            "quantidade": quantidade,
            "status": status_texto,  # <-- só Cadastrado / Alterado / Cancelado
            "dt_emissao": dt_emissao_norm,
            "dt_prog_entr": dt_prog_entr,
            "dt_plan_entr_de": dt_plan_entr_de,
            "dt_plan_entr_ate": dt_plan_entr_ate,
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    # Ordenar por pedido + item_compra
    if not df.empty:
        df = df.sort_values(["pedido", "item_compra"]).reset_index(drop=True)

    return df


uploaded_files = st.file_uploader(
    "Envie um ou mais arquivos XML do pedido",
    type=["xml"],
    accept_multiple_files=True,
)

if uploaded_files:
    all_dfs = []
    for f in uploaded_files:
        st.write(f"📄 Processando: **{f.name}**")
        df_file = parse_arezzo_xml(f)
        if df_file.empty:
            st.warning(f"Nenhum item encontrado em {f.name}")
        else:
            st.success(f"{len(df_file)} item(s) lido(s) em {f.name}")
            all_dfs.append(df_file)

    if all_dfs:
        df_all = pd.concat(all_dfs, ignore_index=True)

        st.subheader("Tabela de Itens (Consolidado)")
        st.dataframe(df_all, use_container_width=True)

        # CSV download (sem gravar no disco → evita PermissionError)
        csv_buffer = StringIO()
        df_all.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        csv_data = csv_buffer.getvalue()

        st.download_button(
            label="⬇️ Baixar CSV (orders.csv)",
            data=csv_data,
            file_name="orders.csv",
            mime="text/csv",
        )
    else:
        st.info("Nenhum item válido foi encontrado nos XML enviados.")
else:
    st.info("Envie um ou mais XMLs para começar.")
