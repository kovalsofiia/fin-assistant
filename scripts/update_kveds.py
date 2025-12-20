import json
import urllib.request
import os

URL = "https://data.gov.ua/dataset/f8a741b9-af17-48e2-8178-8e161c244549/resource/878a36b5-31af-4c36-86e6-5dbf432e9331/download/kved.json"

def fetch_data():
    print(f"Fetching data from {URL}...")
    with urllib.request.urlopen(URL) as response:
        return json.loads(response.read().decode('utf-8'))

def transform(data):
    sections = {}
    
    # First pass: map everything
    for entry in data:
        section_code = entry.get("Код секції")
        division_code = entry.get("Код розділу \n")
        group_code = entry.get("Код групи \n")
        class_code = entry.get("Код класу")
        name = entry.get("Назва", "")

        if not section_code:
            continue

        if section_code not in sections:
            sections[section_code] = {"id": section_code, "title": f"Секція {section_code}. {name}", "groups": {}}
        
        section = sections[section_code]

        if division_code and not group_code and not class_code:
            # It's a Division (Розділ) - which we use as groups in out UI
            if division_code not in section["groups"]:
                section["groups"][division_code] = {"id": division_code, "title": name, "items": []}
            else:
                section["groups"][division_code]["title"] = name

        elif class_code:
            # It's a Class (Item)
            # We need to find or create the division/group this belongs to
            # Usually division is first 2 digits of class code
            div = class_code[:2]
            if div not in section["groups"]:
                section["groups"][div] = {"id": div, "title": f"Розділ {div}", "items": []}
            
            section["groups"][div]["items"].append({
                "code": class_code,
                "name": name,
                "allowedGroups": [2, 3] # Defaulting to common FOP groups
            })

    # Convert dicts back to sorted lists
    final_list = []
    for s_code in sorted(sections.keys()):
        s = sections[s_code]
        s_groups = []
        for g_code in sorted(s["groups"].keys()):
            g = s["groups"][g_code]
            if g["items"]: # Only include groups that have classes
                s_groups.append(g)
        
        if s_groups:
            s["groups"] = s_groups
            final_list.append(s)
            
    return final_list

def main():
    raw_data = fetch_data()
    transformed_data = transform(raw_data)
    
    output_path = "/Users/tsiptakvyacheslav/Sofiia_Practice/fin-assistant/frontend/src/constants/kveds.js"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("export const KVED_SECTIONS = ")
        json.dump(transformed_data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    
    print(f"Successfully updated {output_path}")

if __name__ == "__main__":
    main()
