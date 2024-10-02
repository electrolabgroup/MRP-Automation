# %%
#Api Get Method - Stock Ledger Entry - Mahape
import requests
import pandas as pd
import time 
start_time = time.time()

base_url = 'https://erpv14.electrolabgroup.com/'
endpoint = 'api/resource/Stock Ledger Entry'
url = base_url + endpoint

params = {
    'fields': '["item_code","warehouse","qty_after_transaction","posting_datetime"]',
    'limit_start': 0, 
    'limit_page_length': 1000000000000000,
    'filters': '[["warehouse", "=", "Mahape - EIPL"]]'
}

headers = {
    'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'
}
response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    mahape_ledger = pd.DataFrame(data['data'])
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
    print("Response:", response.json())


# %%
mahape_ledger.head()

# %%
mahape_ledger_sorted = mahape_ledger.sort_values(by='posting_datetime', ascending = False)

mahape_ledger_unique = mahape_ledger_sorted.drop_duplicates(subset='item_code', keep='first')
mahape_ledger_unique.head()

# %%
#Api Get Method - Mahape Item  -  1 
import requests
import pandas as pd
import time 
start_time = time.time()

base_url = 'https://erpv14.electrolabgroup.com/'
endpoint = 'api/resource/Item'
url = base_url + endpoint

params = {
    'fields': '["item_name","item_code","item_defaults.default_warehouse"]',
    'limit_start': 0, 
    'limit_page_length': 10000000000000,
    'filters': '[["disabled", "=", "No"], ["item_name", "not like", "%unprocessed%"]]'
}

headers = {
    'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'
}
response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    mahape_item_df = pd.DataFrame(data['data'])
    mahape_item_df = mahape_item_df[mahape_item_df['default_warehouse'] == 'Mahape - EIPL']
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
    print("Response:", response.json())


# %%
mahape_item_df.head()

# %%
mahape = pd.merge(mahape_item_df,mahape_ledger_unique , on='item_code', how='outer')
mahape.rename(columns={'qty_after_transaction': 'Mahape Quantity'}, inplace=True)
mahape

# %%
##-----------------------------------  Quality Control


# %%
#Api Get Method - Stock Ledger Entry - Quality Control
import requests
import pandas as pd
import time 
start_time = time.time()

base_url = 'https://erpv14.electrolabgroup.com/'
endpoint = 'api/resource/Stock Ledger Entry'
url = base_url + endpoint

params = {
    'fields': '["item_code","warehouse","qty_after_transaction","posting_datetime"]',
    'limit_start': 0, 
    'limit_page_length': 1000000000000000,
    'filters': '[["warehouse", "=", "Quality Control - EIPL"]]'
}

headers = {
    'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'
}
response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    qc_ledger = pd.DataFrame(data['data'])
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
    print("Response:", response.json())


# %%
qc_ledger.head()

# %%
qc_ledger_sorted = qc_ledger.sort_values(by='posting_datetime', ascending = False)

qc_ledger_unique = qc_ledger_sorted.drop_duplicates(subset='item_code', keep='first')
qc_ledger_unique.head()

# %%
#Api Get Method - Quality Control - 2
import requests
import pandas as pd
import time 
start_time = time.time()

base_url = 'https://erpv14.electrolabgroup.com/'
endpoint = 'api/resource/Item'
url = base_url + endpoint

params = {
    'fields': '["item_name","item_code","item_defaults.default_warehouse"]',
    'limit_start': 0, 
    'limit_page_length': 10000000000000,
    'filters': '[["disabled", "=", "No"]]'
}

headers = {
    'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'
}
response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    qc_item_df = pd.DataFrame(data['data'])
    qc_item_df = qc_item_df[qc_item_df['default_warehouse'] == 'Quality Control - EIPL']
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
    print("Response:", response.json())


# %%
qc_item_df

# %%
quality_control = pd.merge(qc_item_df,qc_ledger_unique , on='item_code', how='right')
quality_control.rename(columns={'qty_after_transaction': 'QualityControl Quantity'}, inplace=True)
quality_control

# %%
merged_df = pd.merge(mahape,quality_control , on='item_code', how='outer')
merged_df['Mahape Quantity'] = merged_df['Mahape Quantity'].fillna(0)
merged_df['QualityControl Quantity'] = merged_df['QualityControl Quantity'].fillna(0)
merged_df['Stock Mahape + QC'] = merged_df['Mahape Quantity'] + merged_df['QualityControl Quantity']

merged_df.head()

# %%
merged_df = merged_df[['item_code', 'Mahape Quantity', 'QualityControl Quantity', 'Stock Mahape + QC']]
merged_df

# %%
########---------


# %%
#Api Get Method - purchase order -1
import requests
import pandas as pd
import time 
start_time = time.time()

base_url = 'https://erpv14.electrolabgroup.com/'
endpoint = 'api/resource/Purchase Order'
url = base_url + endpoint

params = {
    'fields': '["items.item_code","items.qty","items.received_qty"]',
    'limit_start': 0, 
    'limit_page_length': 1000000000000,
    'filters': '[["status", "IN", ["To Receive and Bill", "To Receive"]]]'
}

headers = {
    'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'
}
response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    rnb_df = pd.DataFrame(data['data'])
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
    print("Response:", response.json())


# %%
rnb_df = rnb_df.groupby('item_code').sum()

rnb_df.head()

# %%
rnb_df['Pending Qty'] = rnb_df['qty'] - rnb_df['received_qty']
rnb_df.head()

# %%
rnb_df = rnb_df.reset_index()
rnb_df = rnb_df[['item_code', 'Pending Qty']]
rnb_df.head()

# %%
result_df = pd.merge(merged_df,rnb_df, on='item_code', how='outer')
result_df.head()

# %%
result_df['Pending Qty'] = result_df['Pending Qty'].fillna(0)
result_df['Total'] = result_df['Stock Mahape + QC'] + result_df['Pending Qty']

result_df

# %%
### Pending quantity from subcontracting order
## Filter status: Partially Received and Material Transferred
## Call here from subcontractiing order 

# %%
#Api Get Method - Subcontracting Order
import requests
import pandas as pd
import time 
base_url = 'https://erpv14.electrolabgroup.com/'
endpoint = 'api/resource/Subcontracting Order'
url = base_url + endpoint

params = {
    'fields': '["supplier_name","items.item_code","items.qty","items.received_qty"]',
    'limit_start': 0, 
    'limit_page_length': 1000000000000000,
    'filters': '[["status", "in", ["Partially Received", "Material Transferred"]]]'
}

headers = {
    'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'
}
response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    so_df = pd.DataFrame(data['data'])
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
    print("Response:", response.json())


# %%
so_df['SO PENDING QTY'] = so_df['qty'] - so_df['received_qty']
so_df

# %%
import pandas as pd

# Assuming so_df is already defined and contains the necessary columns
so_df_grouped = so_df.groupby('item_code', as_index=False).agg({
    'SO PENDING QTY': 'sum',
    'supplier_name': ', '.join  
})

empty_row = pd.DataFrame([['', '']], columns=['item_code', 'supplier_name'])  # Adjust columns as necessary

so_df_grouped = pd.concat([so_df_grouped, empty_row], ignore_index=True)

so_df_grouped


# %%
# Create the dictionary with desired format
so_df_grouped['Dictionary'] = so_df_grouped.apply(
    lambda row: {f"{supplier.strip()}": row['SO PENDING QTY'] for supplier in row['supplier_name'].split(',')},
    axis=1
)

# Display the updated DataFrame
so_df_grouped


# %%
### Group by item_code annd sum pending quanity 

# %%
## Dictionary column {item code: {warhouse: pneing quanity and total quanity}}, this will be a column in the the result_df 

# %%
result_df = pd.merge(result_df,so_df_grouped , on='item_code', how='outer')

# %%
result_df = result_df.fillna({
    'item_code': '', 
    'supplier_name': '',
    'SO PENDING QTY':0,
    'Mahape Quantity': 0,  # 0 for numeric columns
    'QualityControl Quantity': 0,
    'Stock Mahape + QC': 0,
    'Pending Qty': 0,
    'Total': 0,
    'Dictionary':''    
})
# result_df['item_name'] = result_df['item_name'].apply(lambda x: x[:100] if isinstance(x, str) else x)
result_df['Total'] = result_df['Total'] + result_df['SO PENDING QTY']
result_df

# %%
result_df = result_df[result_df['item_code'].notna() & (result_df['item_code'] != '')]
result_df

# %%
import psycopg2
from psycopg2 import sql, Error
import json

def create_table_if_not_exists(cursor):
    create_table_query = """
    CREATE TABLE IF NOT EXISTS result_df (
        item_code VARCHAR(255),
        so_pending_qty FLOAT,
        mahape_quantity FLOAT,
        qualitycontrol_quantity FLOAT,
        stock_mahape_qc FLOAT,
        pending_qty FLOAT,
        total FLOAT,
        dictionary JSON
    );
    """
    cursor.execute(create_table_query)

# Function to insert data
def insert_data(cursor, result_df):
    insert_query = """INSERT INTO result_df (Dictionary, item_code, so_pending_qty, mahape_quantity, qualitycontrol_quantity, stock_mahape_qc, pending_qty, total)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    
    for index, row in result_df.iterrows():
        supplier_dict = row['Dictionary']

        if not isinstance(supplier_dict, dict):
            supplier_dict = None

        supplier_dict_json = json.dumps(supplier_dict)

        cursor.execute(insert_query, (
            supplier_dict_json,
            row['item_code'], 
            row['SO PENDING QTY'],
            row['Mahape Quantity'], 
            row['QualityControl Quantity'], 
            row['Stock Mahape + QC'],
            row['Pending Qty'],
            row['Total']
        ))

try:
    connection = psycopg2.connect(
        host='192.168.2.11',
        port=5432,
        database='postgres',
        user='postgres', 
        password='admin@123'
    )
    
    if connection:
        print("Connected to PostgreSQL")

        cursor = connection.cursor()

        create_table_if_not_exists(cursor)

        cursor.execute("TRUNCATE TABLE result_df")
        print("Table emptied")
        
        insert_data(cursor, result_df)

        connection.commit()
        print("Data inserted into PostgreSQL table")

except Error as e:
    print(f"Error: {e}")
finally:
    if connection:
        cursor.close()
        connection.close()
        print('Connection closed.')

print('Ledger Done')
