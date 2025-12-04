import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import StringIO

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

def parse_arezzo_xml(file) -> pd.DataFrame:
    """Parse a single Arezzo PO XML into an item-level DataFrame."""
    tree = ET.parse(file)
    root = tree.getroot()

    # --- Header (Pedido_Compra) ---
    header_access = root.find(".//STATEMENT_PEDIDO_COMPRA/Pedido_Compra/access")
    if header_access is None:
        return pd.DataFrame()  # nothing useful

    header = {elem.tag: (elem.text or "").strip() for elem in header_access}

    # Optional: normalize DT_EMISSAO from TO_DATE('03102025','DDMMYYYY') → 03/10/2025
    def parse_to_date(raw: str) -> str:
        # raw example: "TO_DATE('03102025','DDMMYYYY')"
        if not raw or "TO_DATE" not in raw:
            return raw
        try:
            inside = raw.split("TO_DATE(")[1].split(")")[0]
            date_str = inside.split("'")[1]  # 03102025
            # DDMMYYYY
            dd = date_str[0:2]
            mm = date_str[2:4]
            yyyy = date_str[4:8]
            return f"{dd}/{mm}/{yyyy}"
        except Exception:
            return raw

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
            quantidade = int(quantidade_str)
        except ValueError:
            quantidade = None

        # Status mapeado
        status_codigo = row_raw.get("STATUS_ITEM_PEDD", "")
        status_texto = STATUS_MAP.get(status_codigo, status_codigo)

        # Cores: tudo depois do "|"
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
            "status": status_texto,  # <-- só texto, sem número
            "dt_emissao": dt_emissao_norm,
            "dt_prog_entr": dt_prog_entr,
            "dt_plan_entr_de": dt_plan_entr_de,
            "dt_plan_entr_ate": dt_plan_entr_ate,
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    # Ordenar por pedido + item
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

        # CSV download (sem gravar em disco → evita PermissionError)
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
