import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Gerador de orders.csv",
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

# ---------- Helpers ----------

def load_existing() -> pd.DataFrame:
    csv_path = Path("orders.csv")
    if not csv_path.exists():
        return pd.DataFrame(columns=COLUMNS)

    df = pd.read_csv(csv_path, dtype=str)
    df = df.apply(lambda col: col.astype(str).str.strip())
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[COLUMNS]


def parse_azzas_blocks(raw: str):
    """
    Recebe uma ou mais linhas coladas do sistema (com tabs e/ou quebras de linha)
    e retorna uma lista de dicts, 1 por pedido.
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


def main():
    st.title("📦 Gerador de orders.csv a partir da linha AZZAS")

    st.markdown(
        """
        **Como usar:**

        1. Na tela de pedidos (AZZAS / SAP), copie **1 ou vários pedidos**.
        2. Cole o conteúdo **exatamente** no campo abaixo.
        3. Clique em **Gerar / Atualizar CSV**.
        4. O app vai criar/atualizar o arquivo `orders.csv` e permitir o download.

        Cada pedido precisa ter estes 9 campos no total:

        1. Pedido  
        2. Emissão  
        3. Marca  
        4. Fabricante  
        5. Destino  
        6. Status  
        7. Qtd Pedido  
        8. Qtd Faturado  
        9. Alteração  

        Exemplo de bloco de um pedido (com quebras de linha no meio, como costuma vir do sistema):

        ```
        4501644489\t04/07/2025\tRESERVA GO
        5023016 - Cook Street Sourcing...
        1025 - AREZZO\tAlterado\t1002\t0\t27/11/2025
        ```
        """
    )

    raw = st.text_area(
        "Cole aqui os pedidos (1 ou vários)",
        height=220,
        placeholder="Cole aqui exatamente o que você copia da tela de pedidos..."
    )

    if st.button("Gerar / Atualizar CSV"):
        if not raw.strip():
            st.error("Cole pelo menos um pedido antes de continuar.")
            return

        try:
            records = parse_azzas_blocks(raw)
        except ValueError as e:
            st.error(str(e))
            return

        df_existing = load_existing()
        df = df_existing.copy()

        novos = 0
        atualizados = 0

        if df.empty:
            df = pd.DataFrame(records, columns=COLUMNS)
            novos = len(records)
        else:
            for rec in records:
                pedido = rec["Pedido"]
                mask = df["Pedido"] == pedido
                if mask_any := mask.any():
                    for col in COLUMNS:
                        df.loc[mask, col] = rec[col]
                    atualizados += 1
                else:
                    df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
                    novos += 1

        # Salva localmente (quando rodando na sua máquina)
        df.to_csv("orders.csv", index=False, encoding="utf-8-sig")

        st.success(
            f"CSV gerado/atualizado com sucesso! "
            f"Novos pedidos: {novos} · Atualizados: {atualizados} · Total no CSV: {len(df)}"
        )

        st.download_button(
            "⬇️ Baixar orders.csv",
            data=df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="orders.csv",
            mime="text/csv"
        )

        st.markdown("Prévia das últimas linhas do CSV:")
        st.dataframe(df.tail(20), use_container_width=True)


if __name__ == "__main__":
    main()
