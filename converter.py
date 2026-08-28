import io
import re
import pandas as pd
import pypdf
from PIL import Image
import easyocr # pip install easyocr pypdf pandas pillow

def extract_listone_to_csv(pdf_path, output_csv="listone_masterdata.csv"):
    reader = pypdf.PdfReader(pdf_path)
    reader_ocr = easyocr.Reader(['it', 'en'])
    
    all_rows = []
    
    print("Inizio estrazione dal PDF...")
    for page_idx, page in enumerate(reader.pages):
        print(f"Elaborazione pagina {page_idx + 1}/{len(reader.pages)}...")
        for img_obj in page.images:
            img = Image.open(io.BytesIO(img_obj.data))
            # OCR lettura del testo dall'immagine
            results = reader_ocr.readtext(img_obj.data, detail=0)
            
            # Parsing righe
            for line in results:
                # Esempio riga: "#1 P(Por) Bijlow Genoa 18(18) 8(8)"
                # Pattern regex per separare: Ruolo, Nome, Squadra, FVM, Quotazione
                match = re.search(r'([PDC]\([\w,]+\))\s+(.+?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(\d+)\s+(\d+)', line)
                if match:
                    ruolo, nome, squadra, fvm, quot = match.groups()
                    all_rows.append({
                        "Ruolo": ruolo.strip(),
                        "Nome": nome.strip(),
                        "Squadra": squadra.strip(),
                        "FVM": fvm.strip(),
                        "Quotazione": quot.strip()
                    })

    df = pd.DataFrame(all_rows)
    df.drop_duplicates(inplace=True)
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"Estratti {len(df)} giocatori con successo in '{output_csv}'!")
    return df

if __name__ == "__main__":
    extract_listone_to_csv("Listone.pdf")