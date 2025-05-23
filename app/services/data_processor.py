import re
from datetime import datetime

class MarketDataProcessor:
    @staticmethod
    def parse_raw_data(raw_data):
        """Parse raw scraped data into structured format."""
        lines = raw_data.split('\n')
        data = {
            'capital': '',
            'population': 0,
            'urban_population': 0,
            'area': 0,
            'official_languages': '',
            'business_languages': '',
            'other_languages': '',
            'economy_type': '',
            'hdi_rank': '',
            'hdi_value': '',
            'currency': '',
            'usd_rate': '',
            'eur_rate': '',
            'computers_per_100': '',
            'phone_lines_per_100': '',
            'internet_users_per_100': '',
            'telephone_code': '',
            'internet_suffix': '',
            'trade_data': []
        }

        # Process line by line
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Capital
            if line.startswith('Capital:'):
                data['capital'] = line.split(':')[1].strip()
            
            # Population
            elif 'Total Population:' in line:
                population = re.search(r'Total Population: ([\d,]+)', line)
                if population:
                    data['population'] = int(population.group(1).replace(',', ''))
            
            # Urban Population
            elif 'Urban Population:' in line:
                urban_pop = re.search(r'Urban Population: ([\d.]+)%', line)
                if urban_pop:
                    data['urban_population'] = float(urban_pop.group(1))
            
            # Area
            elif line.startswith('Area:'):
                area = re.search(r'Area: ([\d,]+)', line)
                if area:
                    data['area'] = int(area.group(1).replace(',', ''))
            
            # Languages
            elif line.startswith('Official Language:'):
                data['official_languages'] = line.split(':')[1].strip()
            elif line.startswith('Business Language(s):'):
                data['business_languages'] = line.split(':')[1].strip()
            elif line.startswith('Other Languages Spoken:'):
                data['other_languages'] = line.split(':')[1].strip()
            
            # Economy
            elif line.startswith('Type of Economy:'):
                data['economy_type'] = line.split(':')[1].strip()
            
            # HDI
            elif line.startswith('HDI*:'):
                data['hdi_value'] = line.split(':')[1].strip()
            elif line.startswith('HDI (World Rank):'):
                data['hdi_rank'] = line.split(':')[1].strip()
            
            # Currency and Exchange Rates
            elif 'National Currency:' in line:
                currency_match = re.search(r'National Currency: ([^(]+)', line)
                if currency_match:
                    data['currency'] = currency_match.group(1).strip()
            elif 'USD' in line:
                usd_rate = re.search(r'1 [A-Z]{3} = ([\d.]+) USD', line)
                if usd_rate:
                    data['usd_rate'] = usd_rate.group(1)
            elif 'EUR' in line:
                eur_rate = re.search(r'1 [A-Z]{3} = ([\d.]+) EUR', line)
                if eur_rate:
                    data['eur_rate'] = eur_rate.group(1)
            
            # Telecommunication
            elif 'Computers:' in line:
                computers = re.search(r'Computers: ([\d.]+)', line)
                if computers:
                    data['computers_per_100'] = computers.group(1)
            elif 'Telephone Lines:' in line:
                phones = re.search(r'Telephone Lines: ([\d.]+)', line)
                if phones:
                    data['phone_lines_per_100'] = phones.group(1)
            elif 'Internet Users:' in line:
                internet = re.search(r'Internet Users: ([\d.]+)', line)
                if internet:
                    data['internet_users_per_100'] = internet.group(1)
            
            # Contact Info
            elif line.startswith('To call'):
                data['telephone_code'] = line
            elif line.startswith('Internet Suffix:'):
                data['internet_suffix'] = line.split(':')[1].strip()

            # Trade Data
            elif 'Foreign Trade Indicators' in line:
                # Process the next 5 lines for trade data
                trade_lines = lines[i:i+6]  # Include header and 5 data rows
                if len(trade_lines) >= 6:
                    # Process each trade indicator
                    indicators = ['Imports of Goods', 'Exports of Goods', 
                                'Imports of Services', 'Exports of Services']
                    for j, indicator in enumerate(indicators):
                        if indicator in trade_lines[j+1]:
                            values = re.findall(r'(\d+,?\d*)', trade_lines[j+1])
                            if len(values) >= 5:
                                data['trade_data'].append({
                                    'indicator': indicator,
                                    'y2019': int(values[0].replace(',', '')),
                                    'y2020': int(values[1].replace(',', '')),
                                    'y2021': int(values[2].replace(',', '')),
                                    'y2022': int(values[3].replace(',', '')),
                                    'y2023': int(values[4].replace(',', ''))
                                })

        return data

    @staticmethod
    def format_number(value):
        """Format large numbers with commas."""
        if isinstance(value, (int, float)):
            return "{:,}".format(value)
        return value 