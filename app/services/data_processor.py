import re
from datetime import datetime
from bs4 import BeautifulSoup

class MarketDataProcessor:
    @staticmethod
    def parse_raw_data(raw_data):
        """
        Parse raw scraped data (dict with 'donnees1_text', 'donnees2_text', and 'trade_table') into a flat dictionary of all fields.
        """
        # If raw_data is a string (legacy), fallback to old logic
        if isinstance(raw_data, str):
            soup = BeautifulSoup(raw_data, 'html.parser')
            donnees1 = soup.find(id="donnees1")
            donnees2 = soup.find(id="donnees2")
            trade_table = soup.find('table')
        else:
            donnees1_text = raw_data.get('donnees1_text', '')
            donnees2_text = raw_data.get('donnees2_text', '')
            trade_table = raw_data.get('trade_table', [])
            donnees1 = BeautifulSoup(donnees1_text, 'html.parser')
            donnees2 = BeautifulSoup(donnees2_text, 'html.parser')

        data = {}

        def normalize_key(key):
            key = key.strip().replace(':', '').replace('(', '').replace(')', '')
            key = key.lower().replace(' ', '_').replace('/', '_').replace('-', '_')
            key = re.sub(r'[^a-z0-9_]', '', key)
            return key

        # Helper to extract all sous-titre-encart and their values from a section
        def extract_section(section):
            if not section:
                return {}
            section_data = {}
            for div in section.find_all('div', class_='titre-donnees'):
                label = div.find('span', class_='sous-titre-encart')
                if label:
                    key = normalize_key(label.get_text())
                    # Get all text after the label
                    value = label.next_sibling
                    if value is None:
                        # Sometimes value is in the next span or text
                        value = ''.join([str(x) for x in label.parent.find_all(string=True, recursive=False)]).strip()
                    else:
                        value = value.strip() if isinstance(value, str) else value.get_text(strip=True)
                    # If still empty, try all text in div after label
                    if not value:
                        value = div.get_text(separator=' ', strip=True).replace(label.get_text(), '').strip()
                    section_data[key] = value
            return section_data

        # Extract donnees1 and donnees2
        data.update(extract_section(donnees1))
        data.update(extract_section(donnees2))

        # Extract special fields in donnees1 (capital, area, etc.)
        if donnees1:
            for p in donnees1.find_all('p'):
                key = normalize_key(p.get('id', p.get_text().split(':')[0]))
                value = p.get_text().split(':', 1)[-1].strip() if ':' in p.get_text() else p.get_text().strip()
                if key and value:
                    data[key] = value
            # Extract area if present
            for div in donnees1.find_all('div', class_='titre-donnees'):
                if 'Area:' in div.get_text():
                    area_val = re.search(r'Area:\s*([\d,]+)', div.get_text())
                    if area_val:
                        data['area'] = area_val.group(1).replace(',', '')

        # Extract special fields in donnees2 (access to electricity, etc.)
        if donnees2:
            for div in donnees2.find_all('div', class_='titre-donnees'):
                if 'Access to Electricity:' in div.get_text():
                    elec_val = re.search(r'Access to Electricity:\s*([\d,.]+)', div.get_text())
                    if elec_val:
                        data['access_to_electricity'] = elec_val.group(1)

        # Extract Foreign Trade Table
        data['trade_table'] = []
        if trade_table and hasattr(trade_table, 'find_all'):
            headers = [th.get_text(strip=True) for th in trade_table.find_all('th')]
            for row in trade_table.find_all('tr')[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if len(cells) == len(headers):
                    data['trade_table'].append(dict(zip(headers, cells)))
                else:
                    data['trade_table'].append(cells)
        elif isinstance(trade_table, list):
            data['trade_table'] = trade_table

        return data

    @staticmethod
    def format_number(value):
        """Format large numbers with commas."""
        if isinstance(value, (int, float)):
            return "{:,}".format(value)
        return value 