import yfinance as yf
import pandas as pd
import time
import os

# --- 1. IMPORTAZIONE LISTA PERSONALE ---
# Assicurati che il file si chiami 'lista_ticker.csv' e abbia una colonna chiamata 'Ticker'
def carica_lista():
    try:
        # Caricamento da CSV
        df_lista = pd.read_csv('lista_ticker.csv')
        return df_lista['Ticker'].tolist()
    except FileNotFoundError:
        print("Errore: File 'lista_ticker.csv' non trovato. Uso una lista di esempio.")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META"] # Esempio di fallback

def get_val(df, keys):
    for k in keys:
        if k in df.index: return df.loc[k].iloc[0]
    return 0

def run_scanner():
    ticker_list = carica_lista()
    risultati = []
    
    print(f"🚀 Inizio analisi su {len(ticker_list)} titoli dalla tua lista...\n")

    for i, symbol in enumerate(ticker_list):
        symbol = str(symbol).strip().replace('.', '-')
        print(f"[{i+1}/{len(ticker_list)}] Analizzando {symbol}...", end="\r")
        
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # Parametri Fondamentali
            price = info.get('currentPrice', 0)
            if price == 0: continue
            
            roe = info.get('returnOnEquity', 0)
            margin = info.get('profitMargins', 0)
            eps = info.get('trailingEps', 0)
            shares = info.get('sharesOutstanding', 1)
            revenue = info.get('totalRevenue', 1)

            # Owner Earnings (Net Income + Dep - CapEx)
            cf = stock.cashflow
            fina = stock.financials
            ni = get_val(fina, ['Net Income', 'Net Income Common Stockholders'])
            dep = get_val(cf, ['Depreciation And Amortization', 'Depreciation'])
            capex = abs(get_val(cf, ['Capital Expenditure', 'CapEx']))
            
            owner_earnings = ni + dep - capex
            oe_per_share = owner_earnings / shares

            # 2. CALCOLO DEI 3 VALORI INTRINSECHI
            g = 8.5 # Crescita stimata standard
            v_graham = eps * (8.5 + 2 * g)
            v_dcf = (info.get('freeCashflow', owner_earnings) * 15) / shares
            v_buffett = oe_per_share / 0.05 # Tasso sconto 5%
            
            # Media e Margine di Sicurezza (MoS 25%)
            v_medio = (v_graham + v_dcf + v_buffett) / 3
            target_mos = v_medio * 0.75

            # 3. FILTRO SOTTOVALUTAZIONE
            if price <= target_mos:
                sconto = ((v_medio - price) / v_medio) * 100
                risultati.append({
                    "Ticker": symbol,
                    "Prezzo Att.": f"${price:.2f}",
                    "Val. Medio": f"${v_medio:.2f}",
                    "Target MoS": f"${target_mos:.2f}",
                    "Sconto %": round(sconto, 1),
                    "ROE %": round(roe * 100, 1),
                    "Margine %": round(margin * 100, 1),
                    "Owner Earnings": f"${owner_earnings/1e9:.2f}B"
                })
        except:
            continue

    # --- 4. OUTPUT FINALE ---
    print("\n" + "="*60)
    if risultati:
        df_final = pd.DataFrame(risultati)
        # Ordina per il maggior sconto
        df_final = df_final.sort_values(by="Sconto %", ascending=False)
        print("✅ OPPORTUNITÀ TROVATE NELLA TUA LISTA:")
        print(df_final.to_string(index=False))
        # Salvataggio su file per analisi grafica
        df_final.to_csv('risultati_scanner_personale.csv', index=False)
        print(f"\n📁 Risultati salvati in 'risultati_scanner_personale.csv'")
    else:
        print("❌ Nessun titolo della tua lista è attualmente a sconto (MoS 25%).")
    print("="*60)

if __name__ == "__main__":
    run_scanner()