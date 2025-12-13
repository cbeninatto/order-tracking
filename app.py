import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import StringIO
import re
from datetime import datetime

st.set_page_config(page_title="Order XML → CSV", page_icon="📦", layout="wide")

st.title("📦 Pedidos AZZAS – XML → CSV")
st.markdown(
    """
Envie os **XMLs de pedido** (formato Arezzo) e o app irá:

- Ler os itens de todos os pedidos enviados
- Montar uma tabela única já no layout que você definiu
- Permitir download em **pedidas_azzas.csv**
"""
)

STATUS_MAP = {
    "0": "Cadastrado",
    "1": "Alterado",
    "2": "Cancelado",
}

MARCA_MAP = {
    "1": "AREZZO",
    "21": "RESERVA",
    "31": "BRIZZA",
    "4": "ANACAPRI",
    "2": "SCHUTZ",
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

    # Plain numeric YYYYMMDD or DDMMYYYY
    if re.fullmatch(r"\d{8}", raw):
        for fmt in ("%Y%m%d", "%d%m%Y"):
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return raw

    # Already a more "normal" date string: try some patterns
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback: return original string (as-is)
    return raw


def parse_arezzo_xml(file_obj):
    """Parse a single Arezzo PO XML. Retorna header/items/grade/volumes, mas usamos só items na UI."""
    try:
        tree = ET.parse(file_obj)
    except ET.ParseError:
        return {
            "header": pd.DataFrame(),
            "items": pd.DataFrame(),
            "grade": pd.DataFrame(),
            "volumes": pd.DataFrame(),
        }

    root = tree.getroot()

    # ----------------- HEADER -----------------
    header_rows = []
    header_section = root.find("STATEMENT_PEDIDO_COMPRA/Pedido_Compra")
    if header_section is not None:
        for access in header_section.findall("access"):
            row = {elem.tag: (elem.text or "").strip() for elem in access}

            # DT_EMISSAO normalizada + raw
            raw_dt = row.get("DT_EMISSAO", "")
            row["DT_EMISSAO_RAW"] = raw_dt
            row["DT_EMISSAO"] = parse_to_date(raw_dt)

            # PERIODO_ENTREGA normalizado + raw
            raw_periodo = row.get("PERIODO_ENTREGA", "")
            row["PERIODO_ENTREGA_RAW"] = raw_periodo
            row["PERIODO_ENTREGA"] = parse_to_date(raw_periodo)

            header_rows.append(row)

    df_header = pd.DataFrame(header_rows)
    header_map = header_rows[0] if header_rows else {}

    # ----------------- ITEMS -----------------
    item_rows = []
    items_section = root.find("STATEMENT_ITEM_PEDIDO_COMPRA/Item_Pedido_Compra")
    if items_section is not None:
        for access in items_section.findall("access"):
            row = {elem.tag: (elem.text or "").strip() for elem in access}

            # Replicar campos do cabeçalho úteis em cada linha
            for key in [
                "PESSOA_FORNECEDOR",
                "PESSOA_AGENCIADOR",
                "NOME_AGENCIADOR",
                "CONDICAO_PAGTO",
                "DESC_COND_PAGTO",
                "PERIODO_ENTREGA",
                "PERIODO_ENTREGA_RAW",
                "DT_EMISSAO",
                "DT_EMISSAO_RAW",
                "MARCA_IDO",
            ]:
                if key in header_map and key not in row:
                    row[key] = header_map.get(key, "")

            # Status: código + descrição
            status_code = row.get("STATUS_ITEM_PEDD", "")
            row["STATUS_ITEM_PEDD_DESC"] = STATUS_MAP.get(status_code, status_code)

            # Datas do item (normalizada + RAW)
            for date_field in ["DT_PROG_ENTR", "DT_PLAN_ENTR_DE", "DT_PLAN_ENTR_ATE"]:
                raw = row.get(date_field, "")
                row[date_field + "_RAW"] = raw
                row[date_field] = parse_to_date(raw)

            # COR derivada da descrição (texto depois do "|")
            desc_produto = row.get("DESC_PRODUTO", "")
            if "|" in desc_produto:
                row["COR"] = desc_produto.split("|")[-1].strip()
            else:
                row["COR"] = ""

            # Campos numéricos extras (sem perder o texto original)
            for num_field in ["VALOR_UNIT_PRODUTO", "TL_REQU"]:
                val = row.get(num_field, "")
                try:
                    row[num_field + "_NUM"] = float(val.replace(",", "."))
                except Exception:
                    row[num_field + "_NUM"] = None

            item_rows.append(row)

    df_items = pd.DataFrame(item_rows)

    # Grade / Volumes ficam disponíveis se você quiser usar depois
    grade_rows = []
    grade_section = root.find("STATEMENT_GRADE_ITEM_PEDIDO_COMPRA/Grade_Item_Pedido_Compra")
    if grade_section is not None:
        for access in grade_section.findall("access"):
            row = {elem.tag: (elem.text or "").strip() for elem in access}
            q = row.get("QUANTIDADE", "")
            try:
                row["QUANTIDADE_NUM"] = float(q.replace(",", "."))
            except Exception:
                row["QUANTIDADE_NUM"] = None
            grade_rows.append(row)
    df_grade = pd.DataFrame(grade_rows)

    vol_rows = []
    vol_section = root.find("STATEMENT_ITEM_PEDIDO_COMPRA_VOLUMES/Item_Pedido_Compra_Volumes")
    if vol_section is not None:
        for access in vol_section.findall("access"):
            row = {elem.tag: (elem.text or "").strip() for elem in access}
            q = row.get("QUANTIDADE", "")
            try:
                row["QUANTIDADE_NUM"] = float(q.replace(",", "."))
            except Exception:
                row["QUANTIDADE_NUM"] = None
            vol_rows.append(row)
    df_volumes = pd.DataFrame(vol_rows)

    return {
        "header": df_header,
        "items": df_items,
        "grade": df_grade,
        "volumes": df_volumes,
    }


uploaded_files = st.file_uploader(
    "Envie um ou mais arquivos XML do pedido",
    type=["xml"],
    accept_multiple_files=True,
)

if uploaded_files:
    all_items = []

    for f in uploaded_files:
        st.write(f"📄 Processando: **{f.name}**")
        parsed = parse_arezzo_xml(f)

        if not parsed["items"].empty:
            st.success(f"{len(parsed['items'])} item(s) lido(s) em {f.name}")
            all_items.append(parsed["items"])
        else:
            st.warning(f"Nenhum item encontrado em {f.name}")

    df_items_all = pd.concat(all_items, ignore_index=True) if all_items else pd.DataFrame()

    if not df_items_all.empty:
        # Colunas fonte, com nomes originais do XML, na ordem desejada
        simple_cols_src = [
            "DT_EMISSAO",
            "MARCA_IDO",
            "NUM_PEDD_COMPRA",
            "CD_ITEM_MATERIAL",
            "DESC_PRODUTO",
            "COR",
            "DESC_CAT_PRODUTO",
            "DESC_MODELO",
            "CD_COLECAO",
            "CD_LANCAMENTO",
            "GRADE",
            "TL_REQU",
            "VALOR_UNIT_PRODUTO",
            "CONDICAO_PAGTO",
            "STATUS_ITEM_PEDD_DESC",
        ]

        missing = [c for c in simple_cols_src if c not in df_items_all.columns]
        if missing:
            st.warning(
                "As seguintes colunas esperadas não foram encontradas em algum XML: "
                + ", ".join(missing)
            )

        available_cols = [c for c in simple_cols_src if c in df_items_all.columns]
        df_simple = df_items_all[available_cols].copy()

        # ---- Mapear MARCA_IDO para nome da marca ----
        if "MARCA_IDO" in df_simple.columns:
            df_simple["MARCA_NOME"] = (
                df_simple["MARCA_IDO"]
                .astype(str)
                .map(MARCA_MAP)
                .fillna(df_simple["MARCA_IDO"])
            )
        else:
            df_simple["MARCA_NOME"] = ""

        # Renomear para os nomes finais que você definiu
        df_simple = df_simple.rename(
            columns={
                "DT_EMISSAO": "EMISSAO",
                "NUM_PEDD_COMPRA": "NUMERO PEDIDO",
                "CD_ITEM_MATERIAL": "SKU",
                "DESC_PRODUTO": "PRODUTO",
                "COR": "COR",
                "DESC_CAT_PRODUTO": "CATEGORIA",
                "DESC_MODELO": "TIPO",
                "CD_COLECAO": "COLECAO",
                "CD_LANCAMENTO": "LANCAMENTO",
                "GRADE": "GRADE",
                "TL_REQU": "QUANTIDADE",
                "VALOR_UNIT_PRODUTO": "PRECO",
                "CONDICAO_PAGTO": "PAGAMENTO",
                "STATUS_ITEM_PEDD_DESC": "STATUS PEDIDO",
                "MARCA_NOME": "MARCA",
            }
        )

        # Ordem final garantida
        ordered_cols = [
            "EMISSAO",
            "MARCA",
            "NUMERO PEDIDO",
            "SKU",
            "PRODUTO",
            "COR",
            "CATEGORIA",
            "TIPO",
            "COLECAO",
            "LANCAMENTO",
            "GRADE",
            "QUANTIDADE",
            "PRECO",
            "PAGAMENTO",
            "STATUS PEDIDO",
        ]
        df_simple = df_simple[ordered_cols]

        st.subheader("Itens – layout final (pedidas_azzas.csv)")
        st.dataframe(df_simple, use_container_width=True)

        buf_simple = StringIO()
        df_simple.to_csv(buf_simple, index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ Baixar CSV (pedidas_azzas.csv)",
            data=buf_simple.getvalue(),
            file_name="pedidas_azzas.csv",
            mime="text/csv",
        )

        with st.expander("Ver dados completos de itens (debug opcional)"):
            st.dataframe(df_items_all, use_container_width=True)
            buf_full = StringIO()
            df_items_all.to_csv(buf_full, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ Baixar CSV completo de itens (items_full.csv)",
                data=buf_full.getvalue(),
                file_name="items_full.csv",
                mime="text/csv",
            )
    else:
        st.info("Nenhum item válido foi encontrado nos XML enviados.")
else:
    st.info("Envie um ou mais XMLs para começar.")
