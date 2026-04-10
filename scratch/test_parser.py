import pandas as pd
import re

def parse_user_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if not lines:
            return pd.DataFrame()
            
        data = []
        for line in lines[1:]: # Skip header
            parts = line.strip().split()
            if len(parts) < 5: continue
            
            # Registration date is the last two parts (Date Time)
            reg_date = f"{parts[-2]} {parts[-1]}"
            main_parts = parts[:-2] # Everything else
            
            # Constant columns
            num = main_parts[0]
            status = main_parts[1]
            user_id = main_parts[2]
            
            # Remaining parts are Name, Dept, Phone
            remaining = main_parts[3:]
            name = remaining[0] if len(remaining) > 0 else ""
            dept = ""
            phone = ""
            
            next_parts = remaining[1:]
            for p in next_parts:
                if re.match(r'\d{2,3}-\d{3,4}-\d{4}', p):
                    phone = p
                else:
                    dept = p
            
            data.append({
                '순번': num,
                '재직여부': status,
                '아이디': user_id,
                '사용자명': name,
                '부서': dept,
                '전화번호': phone,
                '등록일': reg_date
            })
        
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    filepath = r"c:\Users\김정현\Downloads\Area Analysis 260401\Plant_Area\순번 재직여부 아이디 사용자명 부서 전화번호 등록일 260410.txt"
    df = parse_user_txt(filepath)
    print(df.head(10))
    print(df.tail(5))
