from bs4 import BeautifulSoup
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv('API_KEY')

urls = [
    'https://www.santaelena.com.co/tiendas-pasteleria/tienda-medellin/',
    'https://www.santaelena.com.co/tiendas-pasteleria/tienda-bogota/',
    'https://www.santaelena.com.co/tiendas-pasteleria/tienda-monteria/',
    'https://www.santaelena.com.co/tiendas-pasteleria/tiendas-pastelerias-pereira/',
    'https://www.santaelena.com.co/tiendas-pasteleria/nuestra-pasteleria-en-barranquilla-santa-elena/'
]


def get_coordinates_opencage(address, api_key):
    base_url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": address,
        "key": api_key,
        "limit": 1,
        "no_annotations": 1
    }
    response = requests.get(base_url, params=params)
    result = response.json()
    if result['results']:
        location = result['results'][0]['geometry']
        return [location['lat'], location['lng']]
    else:
        return [None, None]


def simplify_address(address):
    simplified_address = re.sub(r'Local.*$', '', address).strip()
    return simplified_address


def convert_to_24_hour(time_str):
    time_str = time_str.replace("\xa0", " ").replace(" ", "").replace(".", "").lower()
    time_str = re.sub(r'\s*([ap])\s*m\s*\.?', r'\1m', time_str)
    try:
        return datetime.strptime(time_str, '%I:%M%p').strftime('%H:%M')
    except ValueError:
        return time_str


def translate_working_hours(hours):
    days_translation = {
        "lunes a domingos incluye festivos": "Monday to Sunday including holidays",
        "lunes a domingo": "mon - sun",
        "lunes a sábado": "mon - sat",
        "lunes a viernes": "mon - fri",
        "domingos y festivos": "sun and holidays",
        "domingo y festivos": "sun and holidays",
        "domingos": "sun",
        "sábados": "sat",
        "lunes": "mon",
        "martes": "tue",
        "miércoles": "wed",
        "jueves": "thu",
        "viernes": "fri",
        "prestamos servicio 24 horas": "We provide 24 hour service",
        "prestamos servicio las 24 horas": "We provide 24 hour service"
    }

    translated_hours = []

    for hour in hours:
        if hour.strip():
            translated_hour = hour.lower()
            for es_day, en_day in days_translation.items():
                translated_hour = re.sub(rf'\b{es_day}\b', en_day, translated_hour)
            translated_hour = (re.sub(r'\s+', ' ', translated_hour).replace("\xa0", " ").
                               replace("/", "-").replace("–", "-").strip())
            translated_hour = re.sub(r'(\d{1,2}:\d{2}\s*[ap]\s*m\s*\.?)',
                                     lambda x: convert_to_24_hour(x.group(0)),
                                     translated_hour)
            translated_hour = re.sub(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})',
                                     lambda x: f"{convert_to_24_hour(x.group(1))} - {convert_to_24_hour(x.group(2))}",
                                     translated_hour)
            translated_hour = re.sub(r'\s*-\s*', ' - ', translated_hour)
            translated_hours.append(translated_hour.strip())

    return translated_hours


def process_url(url, api_key):
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Не удалось загрузить страницу: {url}")

    soup = BeautifulSoup(response.content, 'html.parser')

    title_tag = soup.find('title')
    city_name = "Unknown City"

    if title_tag:
        title_text = title_tag.get_text()
        match = re.search(r'pasteler[íi]as? en\s*(.+)', title_text, re.IGNORECASE)
        if match:
            city_name = match.group(1).strip()
    else:
        print("No <title> tag found.")

    location_blocks = soup.find_all('div', class_='elementor-widget-container')
    find_location_name = soup.find_all('h3', class_='elementor-heading-title elementor-size-default')

    location_names = [location.get_text(separator=' ', strip=True) for location in find_location_name]

    location_index = 0
    all_locations = []

    for block in location_blocks:
        address_text = None
        phone_text = None
        working_hours = []

        p_elements = block.find_all('p')
        for i, p in enumerate(p_elements):
            text = p.get_text(strip=True)
            if 'Dirección' in text:
                address_text = text.replace('Dirección:', '').strip()
            elif 'Teléfono' in text:
                phone_text = [phone.strip() for phone in text.replace('Teléfono:', '').split(',')]
            elif 'Horario de atención' in text:
                working_hours.append(text.replace('Horario de atención:', '').strip())
                for next_p in p_elements[i + 1:]:
                    next_text = next_p.get_text(strip=True)
                    if next_text:
                        working_hours.append(next_text)

        if not address_text or not phone_text or not working_hours:
            h4_elements = block.find_all('h4')
            for h4 in h4_elements:
                text = h4.get_text(strip=True)
                if 'Dirección' in text or 'Dirección:' in text:
                    next_p = h4.find_next_sibling('p')
                    if next_p:
                        address_text = next_p.get_text(strip=True)
                elif 'Teléfono' in text or 'Teléfono:' in text:
                    next_p = h4.find_next_sibling('p')
                    if next_p:
                        phone_text = [phone.strip() for phone in next_p.get_text(strip=True).split(',')]
                elif 'Horario de atención' in text or 'Horario de atención:' in text:
                    next_p = h4.find_next_sibling('p')
                    if next_p:
                        working_hours_text = next_p.get_text(strip=True)
                        working_hours.extend(p.strip() for p in working_hours_text.split('\n') if p.strip())

        if address_text and phone_text and working_hours:
            translated_hours = translate_working_hours(working_hours)

            if location_index < len(location_names):
                location_name = location_names[location_index]
                location_index += 1
            else:
                location_name = "Unknown Location"

            full_address = f"{city_name}, {address_text}"
            simplified_address = simplify_address(full_address)
            coordinates = get_coordinates_opencage(simplified_address, api_key)

            combined_dict = {
                "name": f"Pastelería Santa Elena {location_name}",
                "address": full_address,
                "latlon": coordinates,
                "phones": phone_text,
                "working_hours": translated_hours,
            }

            all_locations.append(combined_dict)

    return all_locations


def main(urls, api_key):
    all_locations = []

    for url in urls:
        print(f"Processing URL: {url}")
        locations = process_url(url, api_key)
        all_locations.extend(locations)

    with open('santa_elena_locations.json', 'w', encoding='utf-8') as f:
        json.dump(all_locations, f, ensure_ascii=False, indent=2)
    print("Данные успешно сохранены в santa_elena_locations.json")


if __name__ == "__main__":
    main(urls, api_key)
