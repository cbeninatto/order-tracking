import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Rastreamento de Pedidos",
    page_icon="📦",
    layout="centered"
)

COLUMNS = [
    "Pedido",
    "Emissao",
    "Marca",
    "Fabricante",
    "Destino",
    "Status",
    "Qtd_Pedido",
    "Qtd_Faturado",
    "Alteracao",
]

@st.cache_data
def load_orders() -> pd.DataFrame:
    path = Path("orders.csv")
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)

    df = pd.read_csv(path, dtype=str)
    df = df.apply(lambda col: col.astype(str).str.strip())
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[COLUMNS]


def filter_orders(df, pedidos_text, marca, destino):
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    if pedidos_text:
        raw = (
            pedidos_text
            .replace(";", ",")
            .replace(" ", ",")
        )
        pedidos_list = [p.strip() for p in raw.split(",") if p.strip()]
        if pedidos_list:
            mask &= df["Pedido"].isin(pedidos_list)

    if marca:
        mask &= df["Marca"].str.contains(marca, case=False, na=False)

    if destino:
        mask &= df["Destino"].str.contains(destino, case=False, na=False)

    return df[mask]


def main():
    st.title("📦 Rastreamento de Pedidos")

    df = load_orders()
    if df.empty:
        st.info("Nenhum pedido encontrado em `orders.csv` ainda.")
        return

    st.markdown("## 🔍 Consulta")

    with st.form("filtro"):
        col1, col2 = st.columns([2, 1.5])
        with col1:
            pedidos_text = st.text_input(
                "Número(s) do Pedido",
                placeholder="Ex: 4501644489 ou 4501644489, 4501765866"
            )
        with col2:
            marca = st.text_input("Marca (opcional)", placeholder="Ex: RESERVA GO")

        destino = st.text_input("Destino (opcional)", placeholder="Ex: 1025 - AREZZO")
        submitted = st.form_submit_button("Buscar")

    if not submitted:
        st.stop()

    result_df = filter_orders(df, pedidos_text, marca, destino)

    if result_df.empty:
        st.warning("Nenhum pedido encontrado.")
    elif len(result_df) == 1:
        row = result_df.iloc[0]
        st.subheader(f"Pedido {row['Pedido']}")
        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Status", row.get("Status", "-"))
            st.metric("Marca", row.get("Marca", "-"))
            st.metric("Destino", row.get("Destino", "-"))
        with c2:
            st.metric("Emissão", row.get("Emissao", "-"))
            st.metric("Qtd Pedido", row.get("Qtd_Pedido", "-"))
            st.metric("Qtd Faturado", row.get("Qtd_Faturado", "-"))

        st.caption(f"Última atualização: {row.get('Alteracao', '-')}")

        st.markdown("### Detalhes")
        st.dataframe(result_df, use_container_width=True)
    else:
        st.subheader(f"{len(result_df)} pedidos encontrados")
        st.dataframe(result_df, use_container_width=True)


if __name__ == "__main__":
    main()
