import json
import re
import requests
from bs4 import BeautifulSoup


url = 'https://dentalia.com/clinicas'
response = requests.get(url)
if response.status_code != 200:
    raise ValueError(f"Не удалось загрузить страницу: {url}")

soup = BeautifulSoup(response.content, 'html.parser')

clinics = []

clinic_cards = soup.find_all('div', class_='dg-map_clinic-card')

for card in clinic_cards:
    name = card.get('m8l-c-list-name')
    location = card.get('m8l-c-filter-location')
    coords_raw = card.get('m8l-c-list-coord')

    coords = list(map(float, coords_raw.split(',')))

    phone_tag = card.find('a', href=lambda href: href and "tel:" in href)
    phones = [phone.strip() for phone in phone_tag.get_text(strip=True).split(',')] if phone_tag else []

    working_hours = []
    hours_tags = card.find_all('div', class_='dg-map_clinic-card_info_row')

    for row in hours_tags:

        hours_div = row.find_all('div')[1] if len(row.find_all('div')) > 1 else None
        if hours_div:
            hours_text = hours_div.text.strip()
            if ('L-V' in hours_text or 'L-D' in hours_text or 'S-D' in hours_text
                    or 'L, J' in hours_text or 'L-S' in hours_text or 'L y J' in hours_text):

                formatted_hours = hours_text.replace('L-V', 'mon-fri') \
                                            .replace('S-D', 'sat-sun') \
                                            .replace('L-D', 'mon-sun') \
                                            .replace('L, J', 'mon-thu') \
                                            .replace('L-S', 'mon-sat') \
                                            .replace('L y J', 'mon, thu') \
                                            .replace('L', 'mon') \
                                            .replace('M', 'tue') \
                                            .replace('X', 'wed') \
                                            .replace('J', 'thu') \
                                            .replace('V', 'fri') \
                                            .replace('S', 'sat') \
                                            .replace('D', 'sun') \
                                            .replace(' a ', ' - ')

                pattern = r"(\w+-\w+ \d{1,2}:\d{2} - \d{1,2}:\d{2})"
                matches = re.findall(pattern, formatted_hours)
                working_hours.extend(matches)

    clinic = {
        'name': name,
        'address': location,
        'latlon': coords,
        'phones': phones,
        'working_hours': working_hours
    }

    clinics.append(clinic)

with open('dentalia_clinics.json', 'w', encoding='utf-8') as json_file:
    json.dump(clinics, json_file, ensure_ascii=False, indent=4)

print("Данные успешно сохранены в dentalia_clinics.json")
