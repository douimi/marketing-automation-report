#!/usr/bin/env python3
"""
Script to extract all HS codes from draft.html and generate JavaScript data structure
"""

import re
import json

def extract_hs_codes(file_path):
    """Extract all HS codes from the draft.html file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines()]
    
    hs_codes = []
    current_section = None
    current_section_title = None
    current_chapter = None
    current_chapter_title = None
    current_hs4 = None
    current_hs4_title = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
            
        # Section markers (Roman numerals)
        if re.match(r'^[IVX]+$', line):
            current_section = line
            if i + 1 < len(lines):
                current_section_title = lines[i + 1].strip()
                hs_codes.append({
                    'code': current_section,
                    'description': current_section_title,
                    'level': 'section',
                    'chapter': None,
                    'section': current_section
                })
            i += 2
            continue
            
        # Chapter numbers (2 digits)
        if re.match(r'^[0-9]{2}$', line):
            current_chapter = line
            if i + 1 < len(lines):
                current_chapter_title = lines[i + 1].strip()
                hs_codes.append({
                    'code': current_chapter,
                    'description': current_chapter_title,
                    'level': 'chapter',
                    'chapter': current_chapter,
                    'section': current_section
                })
            i += 2
            continue
            
        # HS4 codes (4 digits)
        if re.match(r'^[0-9]{4}$', line):
            current_hs4 = line
            if i + 1 < len(lines):
                current_hs4_title = lines[i + 1].strip()
                hs_codes.append({
                    'code': current_hs4,
                    'description': current_hs4_title,
                    'level': 'hs4',
                    'chapter': current_chapter,
                    'section': current_section
                })
            i += 2
            continue
            
        # HS6 codes (4 digits + dot + 2 digits)
        if re.match(r'^[0-9]{4}\.[0-9]{2}$', line):
            hs6_code = line
            if i + 1 < len(lines):
                hs6_title = lines[i + 1].strip()
                hs_codes.append({
                    'code': hs6_code,
                    'description': hs6_title,
                    'level': 'hs6',
                    'chapter': current_chapter,
                    'section': current_section
                })
            i += 2
            continue
            
        # Skip 'F' separators and other lines
        i += 1
    
    return hs_codes

def generate_javascript_data(hs_codes):
    """Generate JavaScript data structure"""
    js_data = []
    
    for code in hs_codes:
        js_item = {
            'code': code['code'],
            'description': code['description'],
            'level': code['level']
        }
        
        if code['chapter']:
            js_item['chapter'] = code['chapter']
        if code['section']:
            js_item['section'] = code['section']
            
        js_data.append(js_item)
    
    return js_data

def main():
    # Extract HS codes from draft.html
    print("Extracting HS codes from app/draft.html...")
    hs_codes = extract_hs_codes('app/draft.html')
    
    print(f"Extracted {len(hs_codes)} HS codes")
    
    # Generate JavaScript data
    js_data = generate_javascript_data(hs_codes)
    
    # Group by level for statistics
    stats = {}
    for item in js_data:
        level = item['level']
        stats[level] = stats.get(level, 0) + 1
    
    print("Statistics:")
    for level, count in stats.items():
        print(f"  {level}: {count}")
    
    # Save to JSON file for inspection
    with open('hs_codes_data.json', 'w', encoding='utf-8') as f:
        json.dump(js_data, f, indent=2, ensure_ascii=False)
    
    print("Data saved to hs_codes_data.json")
    
    # Generate JavaScript array format
    js_output = "const hsCodesData = [\n"
    for i, item in enumerate(js_data):
        js_output += "    {\n"
        js_output += f'        code: "{item["code"]}",\n'
        js_output += f'        description: "{item["description"].replace('"', '\\"')}",\n'
        js_output += f'        level: "{item["level"]}"'
        
        if 'chapter' in item:
            js_output += f',\n        chapter: "{item["chapter"]}"'
        if 'section' in item:
            js_output += f',\n        section: "{item["section"]}"'
            
        js_output += "\n    }"
        if i < len(js_data) - 1:
            js_output += ","
        js_output += "\n"
    
    js_output += "];"
    
    # Save JavaScript format
    with open('hs_codes_data.js', 'w', encoding='utf-8') as f:
        f.write(js_output)
    
    print("JavaScript data saved to hs_codes_data.js")

if __name__ == "__main__":
    main()
