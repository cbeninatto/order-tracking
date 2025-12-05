import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from io import StringIO
import re
from datetime import datetime

st.set_page_config(page_title="Order XML → CSV", page_icon="📦", layout="wide")

st.title("📦 Order XML → Tabelas de Pedidos (Completo)")
st.markdown(
    """
Envie os **XMLs de pedido** (formato Arezzo) e o app irá:

- Ler **todas** as informações disponíveis (cabeçalho, itens, grade, volumes)
- Gerar tabelas consolidadas para cada tipo de dado
- Permitir download em **CSV** para você filtrar/ajustar depois no Excel ou BI
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

    # Plain numeric YYYYMMDD or DDMMYYYY
    if re.fullmatch(r"\d{8}", raw):
        # Try YYYYMMDD
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
    """Parse a single Arezzo PO XML into multiple DataFrames."""
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
                "MARCA_IDO",  # já existe no item, mas garantimos consistência
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

    # ----------------- GRADE -----------------
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

    # ----------------- VOLUMES -----------------
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
    all_headers = []
    all_items = []
    all_grades = []
    all_volumes = []

    for f in uploaded_files:
        st.write(f"📄 Processando: **{f.name}**")
        parsed = parse_arezzo_xml(f)

        if not parsed["items"].empty:
            st.success(f"{len(parsed['items'])} item(s) lido(s) em {f.name}")
        else:
            st.warning(f"Nenhum item encontrado em {f.name}")

        if not parsed["header"].empty:
            all_headers.append(parsed["header"])
        if not parsed["items"].empty:
            all_items.append(parsed["items"])
        if not parsed["grade"].empty:
            all_grades.append(parsed["grade"])
        if not parsed["volumes"].empty:
            all_volumes.append(parsed["volumes"])

    # Concatena tudo por tipo
    df_header_all = pd.concat(all_headers, ignore_index=True) if all_headers else pd.DataFrame()
    df_items_all = pd.concat(all_items, ignore_index=True) if all_items else pd.DataFrame()
    df_grade_all = pd.concat(all_grades, ignore_index=True) if all_grades else pd.DataFrame()
    df_volumes_all = pd.concat(all_volumes, ignore_index=True) if all_volumes else pd.DataFrame()

    tab_itens, tab_grade, tab_volumes, tab_header = st.tabs(
        ["🧾 Itens", "📏 Grade", "📦 Volumes", "📋 Cabeçalho"]
    )

    # ---------- ITENS ----------
    with tab_itens:
        if not df_items_all.empty:
            st.subheader("Itens (com todos os campos)")
            st.dataframe(df_items_all, use_container_width=True)

            buf = StringIO()
            df_items_all.to_csv(buf, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ Baixar CSV de Itens (items.csv)",
                data=buf.getvalue(),
                file_name="items.csv",
                mime="text/csv",
            )
        else:
            st.info("Nenhum item encontrado nos XML enviados.")

    # ---------- GRADE ----------
    with tab_grade:
        if not df_grade_all.empty:
            st.subheader("Grade por Item")
            st.dataframe(df_grade_all, use_container_width=True)

            buf = StringIO()
            df_grade_all.to_csv(buf, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ Baixar CSV de Grade (grade.csv)",
                data=buf.getvalue(),
                file_name="grade.csv",
                mime="text/csv",
            )
        else:
            st.info("Nenhuma informação de grade encontrada.")

    # ---------- VOLUMES ----------
    with tab_volumes:
        if not df_volumes_all.empty:
            st.subheader("Volumes por Item")
            st.dataframe(df_volumes_all, use_container_width=True)

            buf = StringIO()
            df_volumes_all.to_csv(buf, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ Baixar CSV de Volumes (volumes.csv)",
                data=buf.getvalue(),
                file_name="volumes.csv",
                mime="text/csv",
            )
        else:
            st.info("Nenhuma informação de volumes encontrada.")

    # ---------- CABEÇALHO ----------
    with tab_header:
        if not df_header_all.empty:
            st.subheader("Cabeçalho por Pedido")
            st.dataframe(df_header_all, use_container_width=True)

            buf = StringIO()
            df_header_all.to_csv(buf, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ Baixar CSV de Cabeçalho (header.csv)",
                data=buf.getvalue(),
                file_name="header.csv",
                mime="text/csv",
            )
        else:
            st.info("Nenhuma informação de cabeçalho encontrada.")
else:
    st.info("Envie um ou mais XMLs para começar.")
