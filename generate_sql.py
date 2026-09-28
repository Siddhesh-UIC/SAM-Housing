import pandas as pd
import json

df = pd.read_excel('D:/SAM/SAM-Housing/CRM Data_Solace_Anuj Version_DummyV2.xlsx')

columns = list(df.columns)
# generate SQL schema
sql = ['CREATE TABLE housing_data (']
sql.append('    id INT AUTO_INCREMENT PRIMARY KEY,')

escaped_cols = []
for c in columns:
    safe_c = c.replace(' ', '_').replace('.', '_').replace('-', '_')
    escaped_cols.append(safe_c)
    sql.append(f'    `{safe_c}` TEXT,')
sql[-1] = sql[-1].rstrip(',')
sql.append(');')

sql.append('\n')

df = df.fillna('')
for _, row in df.iterrows():
    vals = []
    for c in columns:
        val = str(row[c]).replace('"', '\\"').replace("'", "\\'")
        vals.append(f"'{val}'")
    
    col_str = ', '.join([f'`{col}`' for col in escaped_cols])
    val_str = ', '.join(vals)
    sql.append(f'INSERT INTO housing_data ({col_str}) VALUES ({val_str});')

# Role creation
sql.append("\nCREATE USER IF NOT EXISTS 'sam_agent'@'%' IDENTIFIED BY 'sam_agent123';")
sql.append("GRANT SELECT ON housing.housing_data TO 'sam_agent'@'%';")
sql.append("FLUSH PRIVILEGES;")

with open('D:/SAM/SAM-Housing/db/init/01_schema.sql', 'w', encoding='utf-8') as f:
    f.write('DROP DATABASE IF EXISTS housing;\nCREATE DATABASE housing;\nUSE housing;\n\n')
    f.write('\n'.join(sql))

print(f'Done generating {len(columns)} columns and {len(df)} rows.')
