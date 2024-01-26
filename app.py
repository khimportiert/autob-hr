#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import fitz  # PyMuPDF
import pytesseract
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import re
from PIL import Image
from tkinter import Tk
from colorama import Fore, Style, init
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
tessdata_dir_config = '--tessdata-dir "/usr/share/tesseract-ocr/4.00/tessdata"'
# sudo apt-get install tesseract-ocr-deu
# sudo apt-get install python3-tk
# pip install googlesearch-python requests beautifulsoup4
# pip install pymupdf pytesseract
# pip install colorama


def is_draft(text):
    word_to_find = 'Entwurf'
    word_count = text.split().count(word_to_find)
    if word_count >= 1:
        return True
    return False

def convert_german_date_to_yyyy_mm(german_date):
    # Mapping von deutschen Monatsnamen zu ihren entsprechenden Nummern
    month_mapping = {
        'Januar': '01',
        'Februar': '02',
        'März': '03',
        'April': '04',
        'Mai': '05',
        'Juni': '06',
        'Juli': '07',
        'August': '08',
        'September': '09',
        'Oktober': '10',
        'November': '11',
        'Dezember': '12',
        'Jan': '01',
        'Feb': '02',
        'Mär': '03',
        'Apr': '04',
        'Mai': '05',
        'Jun': '06',
        'Jul': '07',
        'Aug': '08',
        'Sep': '09',
        'Okt': '10',
        'Nov': '11',
        'Dez': '12'
    }

    # Teilen Sie den deutschen Datumstext in Monat und Jahr auf
    parts = german_date.split()
    month = month_mapping.get(parts[0], '01')  # Standard auf '01' setzen, falls der Monat nicht gefunden wird
    year = parts[1]

    # Konvertieren Sie das deutsche Datum ins gewünschte Format 'yyyy-mm'
    yyyy_mm_date = f"{year}-{month}"

    return yyyy_mm_date

def extract_text_from_first_page_with_ocr(pdf_path):
    doc = fitz.open(pdf_path)

    # Hier gehen wir davon aus, dass die erste Seite des PDFs bei Index 0 liegt
    page = doc[0]

    # Konvertieren Sie die PDF-Seite in ein Bild (zum Beispiel im PNG-Format)
    image = page.get_pixmap()
    image_path = "temp/temp_image.png"
    image.save(image_path)

    # Bild laden
    img = Image.open(image_path)

    # Bildgröße erhalten
    width, height = img.size

    # Zuschneiden auf das obere Drittel
    cropped_img = img.crop((0, 0, width, height // 3))

    # Texterkennung auf dem zugeschnittenen Bild durchführen
    text = pytesseract.image_to_string(cropped_img, lang='deu', config=tessdata_dir_config)

    # Schließen Sie das PDF-Dokument
    doc.close()

    # Löschen Sie das temporäre Bild
    os.remove(image_path)

    return text

def get_html_description(url):
    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            meta_description = soup.find("meta", {"name": "description"})

            if meta_description:
                return meta_description["content"]
            else:
                print("Keine Meta-Beschreibung gefunden.")
                return None

        else:
            print(f"Fehler beim Abrufen der Seite: {response.status_code}")
            return None

    except Exception as e:
        print(f"Fehler: {e}")
        return None

def search_and_get_html_description(query):
    try:
        search_results = list(search(query, num_results=1))

        if not search_results:
            print("Keine Ergebnisse gefunden.")
            return None

        first_link = search_results[0]
        description = get_html_description(first_link)
        return description

    except Exception as e:
        print(f"Fehler: {e}")
        return None

def clean_description(description):
    # Suchen Sie nach dem Index von ". Jetzt informieren!" und extrahieren Sie den Text davor
    index = description.find(". Jetzt informieren!")
    cleaned_description = description[:index].strip() if index != -1 else description.strip()
    return cleaned_description

def split_description(cleaned_description):
    # Muster für Kürzel, Datum und Titel
    pattern = re.compile(r'(DIN EN \d+(\s?\d*)(-\d+)*(\/A\d+)?\s?(Beiblatt \d+|Berichtigung \d+)?)(?: - )?(\d{2,4}-\d{1,2})(?: - )?(.*)')

    match = pattern.match(cleaned_description)

    if match:
        kuerzel = match.group(1)
        datum = match.group(6)
        titel = match.group(7).strip()

        return kuerzel, datum, titel
    else:
        return None, None, None
    
def format_date_01_mm_yy(datum):
    # Formatieren Sie das Datum um in 01.mm.yyyy
    parts = datum.split('-')
    if len(parts) == 2:
        datum = f"01.{parts[1]}.{parts[0]}"
    elif len(parts) == 3:
        datum = f"{parts[2]}.{parts[1]}.{parts[0]}"
    
    return datum

def main():
    r = Tk()
    r.withdraw()
    init() # Initialisiere colorama

    # Replace 'your_pdf_folder_path' with the actual path to your PDF folder
    pdf_folder_path = 'DIN_EN'

    # List PDF files in the folder and sort them by name
    pdf_files = sorted([f for f in os.listdir(pdf_folder_path) if f.endswith('.pdf')])

    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder_path, pdf_file)
        text = extract_text_from_first_page_with_ocr(pdf_path)
        
        name_pattern = re.compile(r'EN \d+(\s?\d*)(-\d+)*(\/A\d+)?\s(Beiblatt \d+|Berichtigung \d+)?')
        date_pattern = re.compile(r'\b(?:Jan(?:uar)?|Feb(?:ruar)?|Mär(?:z)?|Apr(?:il)?|Mai|Jun(?:i)?|Jul(?:i)?|Aug(?:ust)?|Sep(?:tember)?|Okt(?:ober)?|Nov(?:ember)?|Dez(?:ember)?)\s+\d{4}\b')
        name_match = name_pattern.search(text)
        date_match = date_pattern.search(text)

        print(f"Text aus '{pdf_file}':")
        if name_match: 
            name_match = name_match.group().strip()
            if is_draft(text):
                full_name = name_match + " Entwurf"
            else:
                full_name = name_match
            print(full_name)
        if date_match:
            date_match = date_match.group().strip()
            date_match = convert_german_date_to_yyyy_mm(date_match)
            print(date_match)

        # Google query
        prefix = "DIN"
        prefix = prefix + " "
        query = f"beuth.de {prefix}{full_name} - {date_match}"
        description = search_and_get_html_description(query)
        cleaned_description = clean_description(description)
        g_kuerzel, g_datum, g_titel = split_description(cleaned_description)

        if (g_kuerzel is not None) and (g_kuerzel == prefix + name_match) and (g_datum == date_match):
            r.clipboard_append(g_kuerzel)
            print(f"{Fore.BLUE}"+g_kuerzel)
            input("Enter...")

            r.clipboard_append(g_datum)
            print(g_datum)
            input("Enter...")

            r.clipboard_append(g_titel)
            print(g_titel)
            input("Enter...")
        else:
            print("Keine Übereinstimmung gefunden.")
            input("Enter...")

        print("=" * 50)

if __name__ == "__main__":
    main()