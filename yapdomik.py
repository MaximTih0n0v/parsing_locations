import json
from bs4 import BeautifulSoup
import requests

urls = ["https://omsk.yapdomik.ru/about",
        "https://krsk.yapdomik.ru/about",
        "https://achinsk.yapdomik.ru/about",
        "https://berdsk.yapdomik.ru/about",
        "https://nsk.yapdomik.ru/about",
        "https://tomsk.yapdomik.ru/about",
        ]


locations = []

day_mapping = {
    1: 'Пн', 2: 'Вт', 3: 'Ср', 4: 'Чт', 5: 'Пт', 6: 'Сб', 7: 'Вс'
}


def convert_minutes_to_time(minutes):
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours:02}:{minutes:02}"


def format_working_hours(hours):
    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    hours_dict = {}

    for entry in hours:
        day = entry['day']
        day_label = day_mapping.get(day, 'Неизвестно')
        time_range = f"{convert_minutes_to_time(entry['from'])} - {convert_minutes_to_time(entry['to'])}"
        hours_dict[day_label] = time_range

    unique_times = list(set(hours_dict.values()))

    result = []
    if len(unique_times) == 1:
        result.append(f"{days[0]} - {days[-1]} {unique_times[0]}")
    else:
        current_days = []
        last_time = None

        for day in days:
            current_time = hours_dict.get(day, '')
            if current_time == last_time:
                current_days.append(day)
            else:
                if last_time:
                    result.append(f"{current_days[0]} - {current_days[-1]} {last_time}"
                                  if len(current_days) > 1 else f"{current_days[0]} {last_time}")
                current_days = [day]
            last_time = current_time

        result.append(f"{current_days[0]} - {current_days[-1]} {last_time}"
                      if len(current_days) > 1 else f"{current_days[0]} {last_time}")

    return result


def format_hours(hours):
    grouped_hours = {}

    for entry in hours:
        day = entry['day']
        open_time = convert_minutes_to_time(entry['from'])
        close_time = convert_minutes_to_time(entry['to'])

        if day not in grouped_hours:
            grouped_hours[day] = []
        grouped_hours[day].append((open_time, close_time))

    formatted_hours = []
    for day, periods in grouped_hours.items():
        periods = sorted(periods)
        merged_periods = []
        current_start, current_end = periods[0]

        for start, end in periods[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                merged_periods.append(f"{current_start} - {current_end}")
                current_start, current_end = start, end
        merged_periods.append(f"{current_start} - {current_end}")

        formatted_hours.append({
            'day': day,
            'from': int(current_start.split(':')[0]) * 60 + int(current_start.split(':')[1]),
            'to': int(current_end.split(':')[0]) * 60 + int(current_end.split(':')[1])
        })

    return format_working_hours(formatted_hours)


def find_working_hours(address_id, data):
    working_hours = []
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    for i in range(1, 8):
        daily_hours = []
        for wh in data.get('workingHours', []):
            print(f'wh: {wh}')
            if wh['shop_id'] == address_id and wh['shop_id'] == address_id:
                open_time = convert_minutes_to_time(wh['from'])
                print(open_time)
                close_time = convert_minutes_to_time(wh['to'])
                daily_hours.append(f"{open_time} - {close_time}")

        if daily_hours:
            working_hours.append(f"{days_of_week[i - 1]} {' '.join(daily_hours)}")

    if not working_hours:
        print(f"Не найдены рабочие часы для address_id: {address_id}")

    return working_hours


def find_coordinates(address, data):
    for key, value in data.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get('address') == address:
                    coord = item.get('coord', {})
                    latitude = coord.get('latitude', 'Не указана')
                    longitude = coord.get('longitude', 'Не указана')
                    address_id = item.get('id', None)
                    working_hours = item.get('workingHours', [])
                    return latitude, longitude, working_hours, address_id
    print(f"Не найдены координаты и рабочие часы для адреса: {address}")
    return 'Не указана', 'Не указана', [], None


for url in urls:
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError(f"Не удалось загрузить страницу: {url}")

    soup = BeautifulSoup(response.content, 'html.parser')

    json_content = None

    address_block = soup.find('div', class_='site-footer__address-list')

    if not address_block:
        raise ValueError("Не удалось найти блок с адресами суши-баров.")

    city_headers = address_block.find_all('h2')

    city_name = None
    for header in city_headers:
        if header.text.strip().startswith("г."):
            city_name = header.text.strip().replace("г. ", "").replace(":", "").capitalize()
            break

    if not city_name:
        raise ValueError("Не удалось найти название города.")

    phone_block = soup.find('div', class_='contacts__phone')
    phone_numbers = []
    if phone_block:
        phone_link = phone_block.find('a', href=True)
        if phone_link:
            phone_number = phone_link.get_text(strip=True)
            # print(f"Номер телефона: {phone_number}")
            phone_numbers.append(phone_number)

        else:
            print("Не удалось найти номер телефона в блоке.")

    else:
        print("Не удалось найти блок с контактной информацией.")

    address_list = address_block.find_all('ul')

    if not address_list:
        raise ValueError("Не удалось найти список адресов.")

    streets = []
    for address_ul in address_list:
        addresses = address_ul.find_all('li')
        for address in addresses:
            street_address = f"{address.text.strip()}"
            streets.append(street_address)

    for script_tag in soup.find_all('script'):
        script_text = script_tag.string
        if script_text:
            start_index = script_text.find('window.initialState =')
            if start_index != -1:
                start_index += len('window.initialState =')
                end_index = script_text.find('};', start_index) + 1
                if end_index == 0:
                    end_index = len(script_text)
                json_content = script_text[start_index:end_index].strip()
                break

    if json_content:
        try:
            data = json.loads(json_content)
            for address in streets:
                latitude, longitude, working_hours, address_id = find_coordinates(address, data)
                default_hours = [entry for entry in working_hours if entry['type'] == 'default']
                formatted_hours = format_hours(default_hours)

                latlon = [float(latitude), float(longitude)]

                full_address = f"{city_name}, {address}"
                location_data = {
                    "name": "Японский Домик",
                    "address": full_address,
                    "latlon": latlon,
                    "phones": [t for t in phone_numbers],
                    "working_hours": formatted_hours
                }
                locations.append(location_data)

        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON на странице {url}: {e}")

    else:
        print(f"Не удалось найти данные JSON в скрипте на странице {url}.")


with open('yapdomik_locations.json', 'w', encoding='utf-8') as outfile:
    json.dump(locations, outfile, ensure_ascii=False, indent=4)
print("Данные успешно сохранены в yapdomik_locations.json")




