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
    csv_path = Path("orders.csv")
    if not csv_path.exists():
        return pd.DataFrame(columns=COLUMNS)

    df = pd.read_csv(csv_path, dtype=str)
    df = df.apply(lambda col: col.astype(str).str.strip())
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]
    return df


def save_orders(df: pd.DataFrame):
    df = df.copy()
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]
    df.to_csv("orders.csv", index=False)
    load_orders.clear()


def parse_azzas_line(raw: str) -> dict:
    """
    Exemplo de entrada (copiado do sistema, com quebras de linha):

    4501644489\t04/07/2025\tRESERVA GO
    5023016 - Cook Street Sourcing...
    1025 - AREZZO\tAlterado\t1002\t0\t27/11/2025
    """
    if not raw or not raw.strip():
        raise ValueError("Entrada vazia.")

    # Normaliza quebras de linha → tabs
    text = (
        raw.replace("\r\n", "\n")
           .replace("\r", "\n")
           .replace("\n", "\t")
    )

    parts = [p.strip() for p in text.split("\t") if p.strip()]

    if len(parts) != 9:
        raise ValueError(
            f"Esperava 9 campos, mas encontrei {len(parts)}.\n"
            f"Campos detectados: {parts}"
        )

    data = dict(zip(COLUMNS, parts))
    return data


def filter_orders(df, pedidos_text, marca, destino):
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    # Filtro por pedido (suporta múltiplos separados por vírgula/; / espaço)
    if pedidos_text:
        raw = (
            pedidos_text
            .replace(";", ",")
            .replace(" ", ",")
        )
        pedidos_list = [p.strip() for p in raw.split(",") if p.strip()]
        if pedidos_list:
            mask &= df["Pedido"].isin(pedidos_list)

    # Filtro por marca
    if marca:
        mask &= df["Marca"].str.contains(marca, case=False, na=False)

    # Filtro por destino
    if destino:
        mask &= df["Destino"].str.contains(destino, case=False, na=False)

    return df[mask]


def main():
    st.title("📦 Rastreamento de Pedidos")
    st.markdown(
        """
        Consulte o status dos seus pedidos usando o número do **Pedido**, 
        ou filtrando por **Marca** / **Destino**.
        """
    )

    df = load_orders()
    if df.empty:
        st.info(
            "Base de dados ainda vazia ou `orders.csv` não criado. "
            "Use a área **Admin (Atualizar CSV)** abaixo para incluir o primeiro pedido."
        )

    # ------------------ Consulta cliente ------------------
    st.markdown("## 🔍 Consulta de Pedidos")

    with st.form("filtro_pedidos"):
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

    if submitted:
        if df.empty:
            st.warning(
                "Ainda não há pedidos cadastrados. "
                "Use a área de **Admin (Atualizar CSV)** para incluir dados."
            )
        else:
            result_df = filter_orders(df, pedidos_text, marca, destino)

            if result_df.empty:
                st.warning("Nenhum pedido encontrado com os filtros informados.")
            else:
                # 1 resultado → card bonitinho
                if len(result_df) == 1:
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

                    st.caption(f"Última atualização (Alteração): {row.get('Alteracao', '-')}")

                    st.markdown("### Detalhes completos")
                    st.dataframe(result_df, use_container_width=True)

                # Vários resultados → tabela
                else:
                    st.subheader(f"{len(result_df)} pedidos encontrados")
                    st.dataframe(result_df, use_container_width=True)

    st.markdown("---")

    # ------------------ Admin ------------------
    st.markdown("## 🛠️ Admin (Atualizar CSV)")

    with st.expander("Área restrita para atualização da base (orders.csv)", expanded=False):
        st.markdown(
            """
            Cole **exatamente** a linha copiada do sistema (AZZAS / SAP), 1 pedido por vez.  
            Exemplo de formato:

            `4501644489\\t04/07/2025\\tRESERVA GO`
            `5023016 - Cook Street Sourcing...`
            `1025 - AREZZO\\tAlterado\\t1002\\t0\\t27/11/2025`
            """
        )

        raw_input = st.text_area(
            "Linha do pedido (copiar/colar do sistema)",
            height=150,
            placeholder="Cole aqui a linha do pedido...",
        )

        colA, colB = st.columns([1, 1])
        with colA:
            action = st.selectbox(
                "Ação",
                ["Inserir/Atualizar pedido"],
                index=0
            )
        with colB:
            apply_btn = st.button("Aplicar atualização")

        if apply_btn:
            if not raw_input.strip():
                st.error("Por favor, cole a linha do pedido antes de aplicar.")
            else:
                try:
                    record = parse_azzas_line(raw_input)
                except ValueError as e:
                    st.error(f"Erro ao interpretar a linha:\n\n{e}")
                else:
                    df_current = load_orders().copy()

                    if df_current.empty:
                        df_current = pd.DataFrame(columns=COLUMNS)

                    pedido = record["Pedido"]

                    if "Pedido" in df_current.columns:
                        mask = df_current["Pedido"] == pedido
                        if mask.any():
                            # Atualiza linha existente
                            for col in COLUMNS:
                                df_current.loc[mask, col] = record[col]
                            msg = f"Pedido {pedido} atualizado com sucesso."
                        else:
                            # Adiciona nova linha
                            df_current = pd.concat(
                                [df_current, pd.DataFrame([record])],
                                ignore_index=True
                            )
                            msg = f"Pedido {pedido} incluído com sucesso."
                    else:
                        df_current = pd.DataFrame([record], columns=COLUMNS)
                        msg = f"Base criada com o pedido {pedido}."

                    save_orders(df_current)
                    st.success(msg)
                    st.dataframe(df_current.tail(5), use_container_width=True)

    st.caption(
        "Dados armazenados em `orders.csv`. "
        "Para uso em produção (multiusuário / persistência garantida), "
        "considere migrar no futuro para uma planilha online (Google Sheets) ou banco de dados."
    )


if __name__ == "__main__":
    main()
