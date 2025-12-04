import streamlit as st
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# Config
# --------------------------------------------------
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


# --------------------------------------------------
# Data helpers
# --------------------------------------------------
@st.cache_data
def load_orders() -> pd.DataFrame:
    """Load orders.csv if it exists, else empty DF with correct columns."""
    csv_path = Path("orders.csv")
    if not csv_path.exists():
        return pd.DataFrame(columns=COLUMNS)

    df = pd.read_csv(csv_path, dtype=str)
    df = df.apply(lambda col: col.astype(str).str.strip())
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[COLUMNS]


def save_orders(df: pd.DataFrame):
    """Save DataFrame to orders.csv and clear cache."""
    df = df.copy()
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]
    df.to_csv("orders.csv", index=False, encoding="utf-8-sig")
    load_orders.clear()


def parse_azzas_blocks(raw: str):
    """
    Recebe 1 ou vários pedidos colados do sistema (com tabs e/ou quebras de linha)
    e devolve uma lista de dicts (1 por pedido).

    Cada pedido deve ter estes 9 campos no total:
    1. Pedido
    2. Emissao
    3. Marca
    4. Fabricante
    5. Destino
    6. Status
    7. Qtd_Pedido
    8. Qtd_Faturado
    9. Alteracao
    """
    if not raw or not raw.strip():
        raise ValueError("Entrada vazia.")

    # Normaliza quebras de linha -> tabs
    text = (
        raw.replace("\r\n", "\n")
           .replace("\r", "\n")
           .replace("\n", "\t")
    )

    tokens = [t.strip() for t in text.split("\t") if t.strip()]

    if len(tokens) % len(COLUMNS) != 0:
        raise ValueError(
            f"Esperava múltiplos de {len(COLUMNS)} campos (9 por pedido), "
            f"mas encontrei {len(tokens)}. "
            "Verifique se copiou apenas as linhas dos pedidos, sem cabeçalho."
        )

    records = []
    for i in range(0, len(tokens), len(COLUMNS)):
        chunk = tokens[i:i+len(COLUMNS)]
        rec = dict(zip(COLUMNS, chunk))
        records.append(rec)

    return records


def filter_orders(df, pedidos_text, marca, destino):
    """Filters for client-facing search."""
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    # Filtro por Pedido (suporta múltiplos)
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


# --------------------------------------------------
# UI
# --------------------------------------------------
def main():
    st.title("📦 Rastreamento de Pedidos")

    df = load_orders()

    # ------------------ Client search ------------------
    st.markdown("## 🔍 Consulta de Pedidos")

    if df.empty:
        st.info(
            "Ainda não há pedidos em `orders.csv`. "
            "Use a área **Admin** abaixo para incluir o primeiro pedido."
        )

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
            st.warning("Ainda não há pedidos cadastrados.")
        else:
            result_df = filter_orders(df, pedidos_text, marca, destino)

            if result_df.empty:
                st.warning("Nenhum pedido encontrado com os filtros informados.")
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

                st.caption(f"Última atualização (Alteração): {row.get('Alteracao', '-')}")

                st.markdown("### Detalhes completos")
                st.dataframe(result_df, use_container_width=True)
            else:
                st.subheader(f"{len(result_df)} pedidos encontrados")
                st.dataframe(result_df, use_container_width=True)

    st.markdown("---")

    # ------------------ Admin updater ------------------
    st.markdown("## 🛠️ Admin – Atualizar orders.csv colando do AZZAS")

    with st.expander("Clique para abrir a área de atualização", expanded=False):
        st.markdown(
            """
            1. Na tela de pedidos (AZZAS / SAP), copie **1 ou vários pedidos**.  
            2. Cole **exatamente** o conteúdo abaixo (com quebras de linha mesmo).  
            3. Clique em **Aplicar atualização**.

            Cada pedido deve conter, no total, 9 campos nesta ordem:

            1. Pedido  
            2. Emissão  
            3. Marca  
            4. Fabricante  
            5. Destino  
            6. Status  
            7. Qtd Pedido  
            8. Qtd Faturado  
            9. Alteração  

            Exemplo de 1 pedido (como costuma vir do sistema):

            ```
            4501644489\t04/07/2025\tRESERVA GO
            5023016 - Cook Street Sourcing...
            1025 - AREZZO\tAlterado\t1002\t0\t27/11/2025
            ```
            """
        )

        raw_input = st.text_area(
            "Cole aqui os pedidos (1 ou vários)",
            height=220,
            placeholder="Cole aqui direto da tela de pedidos..."
        )

        if st.button("Aplicar atualização"):
            if not raw_input.strip():
                st.error("Cole pelo menos um pedido antes de atualizar.")
            else:
                try:
                    records = parse_azzas_blocks(raw_input)
                except ValueError as e:
                    st.error(str(e))
                else:
                    df_current = load_orders().copy()
                    if df_current.empty:
                        df_current = pd.DataFrame(columns=COLUMNS)

                    novos = 0
                    atualizados = 0

                    for rec in records:
                        pedido = rec["Pedido"]
                        mask = df_current["Pedido"] == pedido

                        if mask.any():
                            for col in COLUMNS:
                                df_current.loc[mask, col] = rec[col]
                            atualizados += 1
                        else:
                            df_current = pd.concat(
                                [df_current, pd.DataFrame([rec])],
                                ignore_index=True
                            )
                            novos += 1

                    save_orders(df_current)

                    st.success(
                        f"Atualização concluída! Novos pedidos: {novos} · "
                        f"Atualizados: {atualizados} · Total no CSV: {len(df_current)}"
                    )

                    st.markdown("Prévia das últimas linhas do CSV:")
                    st.dataframe(df_current.tail(20), use_container_width=True)

                    st.download_button(
                        "⬇️ Baixar orders.csv atualizado",
                        data=df_current.to_csv(index=False, encoding="utf-8-sig"),
                        file_name="orders.csv",
                        mime="text/csv"
                    )

    st.caption(
        "Observação: quando rodando **localmente**, o arquivo `orders.csv` é salvo na pasta do projeto. "
        "Depois é só fazer `git add/commit/push` para atualizar o app público."
    )


if __name__ == "__main__":
    main()
