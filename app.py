from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pandas as pd
import requests
import re
import numpy as np

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a strong secret key

import pandas as pd
import psycopg2

# Function to get result_df from PostgreSQL
def get_result_df():
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='postgres',
        user='postgres',  # Replace with your PostgreSQL username
        password='admin@123'
    )
    
    # Query to select all data from result_df
    query = "SELECT * FROM result_df"
    df = pd.read_sql(query, conn)
    
    # Close the connection
    conn.close()
    
    df['dictionary'] = df['dictionary'].fillna('')    
    # Drop 'id' column if it exists
    if 'id' in df.columns:
        df = df.drop(columns=['id'])
    
    return df


@app.route('/search', methods=['GET'])
def search():
    bom_name = request.args.get('bom_name')
    quantity = int(request.args.get('quantity'))  # Default quantity is 1
    session['item'] = bom_name
    session['qty'] = quantity

    if not bom_name:
        return jsonify({'error': 'BOM name is required'}), 400

    # Step 1: Get result_df from MySQL
    try:
        result_df = get_result_df()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Step 2: Make API call to fetch BOM data
    base_url = 'https://erpv14.electrolabgroup.com/'
    endpoint = 'api/resource/BOM'
    url = base_url + endpoint
    headers = {
        'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'
    }
    params = {
        'fields': '["name","item","items.item_name","items.item_code","items.qty"]',
        'limit_start': 0,
        'limit_page_length': 100000000000,
        'filters': '[["is_default", "=", 1]]'
    }
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        bom_df = pd.DataFrame(data['data'])
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to fetch BOM data'}), 500

    # Filter BOM Data by BOM name
    bom_filtered_df = bom_df[bom_df['item'] == bom_name]
    if bom_filtered_df.empty:
        return jsonify({'message': 'No data found for the provided BOM name'}), 404

    # Step 3: Merge BOM data with result_df
    final_df = pd.merge(bom_filtered_df, result_df, on=['item_code'], how='left')
    final_df = final_df.fillna(0)
    final_df['qty'] = (final_df['qty'] * quantity)

    # Ensure columns are float and round to 3 decimal places
    decimal_columns = [
        'qty',
        'so_pending_qty',
        'mahape_quantity',
        'qualitycontrol_quantity',
        'stock_mahape_qc',
        'pending_qty',
        'total'
    ]

    # Convert to float type if they are not already
    for col in decimal_columns:
        final_df[col] = final_df[col].astype(float)

    # Round columns to 3 decimal places
    final_df[decimal_columns] = final_df[decimal_columns].round(3)

    def rename_and_order_columns(df):
        df = df.rename(columns={
            'so_pending_qty': 'Subcontracting Order Pending Quantity (1)',
            'stock_mahape_qc': 'Stock Mahape & QC (4) [ 2 + 3]',
            'total': 'Total [1 +4 +5]',
            'pending_qty': 'Pending Quantity (5)',
            'qualitycontrol_quantity': 'Quality Control Quantity (3)',
            'mahape_quantity': 'Mahape Quantity (2)',
            'name': 'BOM Name',
            'dictionary':'Dictionary'
        })
        new_column_order = [ 
            'BOM Name',  
            'item',
            'item_name',
            'item_code',
            'qty',
            'Dictionary', 
            'Subcontracting Order Pending Quantity (1)',
            'Mahape Quantity (2)',
            'Quality Control Quantity (3)',
            'Stock Mahape & QC (4) [ 2 + 3]',
            'Pending Quantity (5)',
            'Total [1 +4 +5]'
        ]
        return df[new_column_order]

    # Apply renaming and reordering for final_df
    final_df = rename_and_order_columns(final_df)

    # Function to apply row-based styling
    def color_rows(row):
        color = 'background-color: #ccffcc;' if row['qty'] <= row['Total [1 +4 +5]'] else 'background-color: #ffcccc;'
        return [color] * len(row)

    # Apply styling
    styled_df = final_df.style.apply(color_rows, axis=1).set_table_attributes('class="table table-striped"')

    # Format the float columns to 3 decimal places
    styled_df = styled_df.format({
        'qty':'{:.3f}',
        'Subcontracting Order Pending Quantity (1)': '{:.3f}',
        'Mahape Quantity (2)': '{:.3f}',
        'Quality Control Quantity (3)': '{:.3f}',
        'Stock Mahape & QC (4) [ 2 + 3]': '{:.3f}',
        'Pending Quantity (5)': '{:.3f}',
        'Total [1 +4 +5]': '{:.3f}',
    })

    # Convert styled DataFrame to HTML
    result_html = styled_df.to_html(index=False)

    # Prepare additional tables for item_code rows
    additional_tables_html = ""
    all_item_codes = list(bom_filtered_df['item_name'].unique())
    item_names = set()  

    iteration = 1
    max_iterations = 10  # Limit iterations to avoid excessive processing
    while all_item_codes and iteration <= max_iterations:
        iteration_tables_html = ""
        next_item_codes = set()

        for item_code in all_item_codes:
            additional_data_df = bom_df[bom_df['item'] == item_code]
            if not additional_data_df.empty:
                additional_table_df = pd.merge(additional_data_df, result_df, on=['item_code'], how='left')
                additional_table_df = additional_table_df.fillna(0)
                additional_table_df['qty'] = (additional_table_df['qty'] * quantity).astype(int)

                # Replace item column with item_code
                additional_table_df['item'] = item_code

                # Rename and reorder columns for additional_table_df
                additional_table_df = rename_and_order_columns(additional_table_df)

                # Get the name for the additional table
                item_name = additional_data_df['name'].iloc[0]
                item_names.add(item_name)

                # Apply styling
                styled_additional_table_df = additional_table_df.style.apply(color_rows, axis=1).set_table_attributes('class="table table-striped"')
                # Format the float columns to 3 decimal places
                styled_additional_table_df = styled_additional_table_df.format({
                    'qty':'{:.3f}',
                    'Subcontracting Order Pending Quantity (1)': '{:.3f}',
                    'Mahape Quantity (2)': '{:.3f}',
                    'Quality Control Quantity (3)': '{:.3f}',
                    'Stock Mahape & QC (4) [ 2 + 3]': '{:.3f}',
                    'Pending Quantity (5)': '{:.3f}',
                    'Total [1 +4 +5]': '{:.3f}',
                })
                additional_table_html = styled_additional_table_df.to_html(index=False)

                # Construct HTML for the additional table
                iteration_tables_html += f'<div class="additional-table" data-name="{item_name}"><h4>Data for {item_name}</h4>{additional_table_html}</div>'

                # Collect item codes for the next iteration
                next_item_codes.update(additional_data_df['item_name'].unique())

        if not iteration_tables_html:
            break  # Exit loop if no additional tables were generated

        additional_tables_html += iteration_tables_html
        all_item_codes = list(next_item_codes)  # Update item codes for the next iteration
        iteration += 1

    if iteration > max_iterations:
        additional_tables_html += '<p>.</p>'

    # Convert item_names set to a sorted list
    names = sorted(list(item_names))

    return render_template('result.html', table=result_html, additional_tables=additional_tables_html, names=names, item=bom_name,qty=quantity)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for


@app.route('/display', methods=['GET'])
def display():
    # Access session data
    item = session.get('item')
    qty = session.get('qty')

    if not item or qty is None:
        return redirect(url_for('search'))  # Redirect to search if no data

    # Retrieve result_df from the database
    result_df = get_result_df()
    test_df = result_df.copy()

    # API call to get BOM data
    base_url = 'https://erpv14.electrolabgroup.com/'
    endpoint = 'api/resource/BOM'
    url = base_url + endpoint
    headers = {'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'}
    params = {
        'fields': '["name","item","items.item_name","items.item_code","items.qty"]',
        'limit_start': 0,
        'limit_page_length': 100000000000,
        'filters': '[["is_default", "=", 1]]'
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        bom_df = pd.DataFrame(data['data'])
    else:
        return "Failed to fetch BOM data", 500

    # Filter BOM Data by session item
    filtered_df = bom_df[bom_df['item'] == item]
    filtered_df['qty'] = filtered_df['qty'] * qty

    # Merge with result_df to create merged_df
    final_df = pd.merge(filtered_df, result_df, on=['item_code'], how='left')
    final_df = final_df.fillna(0)

    final_result_df = pd.DataFrame()

    max_iterations = 10
    iteration = 0

    current_df = final_df.copy()

    while iteration < max_iterations:
        matching_rows = []

        for item_name in current_df['item_name']:
            matches = bom_df[bom_df['item'] == item_name]
            
            if not matches.empty:
                matching_rows.append(matches)

        result_df = pd.concat(matching_rows, ignore_index=True) if matching_rows else pd.DataFrame()

        if result_df.empty:
            break

        final_result_df = pd.concat([final_result_df, result_df], ignore_index=True)

        current_df = result_df

        iteration += 1

    if final_result_df.empty:
        final_result_df = pd.DataFrame(columns=['item_code'])
    
    final_result_df = pd.merge(final_result_df, test_df, on=['item_code'], how='left')

    combined_df = pd.concat([filtered_df, final_result_df], ignore_index=True)
    combined_df = combined_df.groupby(['item_name', 'item_code'])[['qty', 'total']].sum().reset_index()
    combined_df = combined_df.reset_index()
    endpoint = 'api/resource/Purchase Receipt'
    url = base_url + endpoint

    params = {
        'fields': '["posting_date","items.item_code","items.rate"]',
        'limit_start': 0, 
        'limit_page_length': 1000000000000000,
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        purchase_df = pd.DataFrame(data['data'])
        purchase_df = purchase_df.sort_values(by='posting_date', ascending=False)
        purchase_df = purchase_df.drop_duplicates(subset='item_code', keep='first')
    else:
        return "Failed to fetch purchase receipt data", 500

    # Merge combined_df with purchase_df
    merged_df = pd.merge(combined_df, purchase_df, on='item_code', how='left')
    merged_df = merged_df.fillna(0)

    # Calculate fields
    merged_df['QTY Defecit'] = merged_df['qty'] - merged_df['total']
    merged_df['Amount of Item to Purchase'] = merged_df['QTY Defecit'] * merged_df['rate']
    merged_df['Total Cost'] = merged_df['qty'] * merged_df['rate']
    merged_df = merged_df.drop(columns=['posting_date'])

    # Reorder columns
    new_order = [
        'item_name', 
        'item_code', 
        'qty', 
        'total', 
        'rate', 
        'Total Cost', 
        'QTY Defecit', 
        'Amount of Item to Purchase'
    ]

    merged_df = merged_df[new_order]
    total_df = merged_df.copy()
    total_df['Total Cost'] = total_df['Total Cost'].clip(lower=0)
    total_df['Amount of Item to Purchase'] = total_df['Amount of Item to Purchase'].clip(lower=0)

    total_df.replace(-0.00, 0, inplace=True)
    total_df = pd.DataFrame({
        'Total Cost': [total_df['Total Cost'].sum()],
        'Amount of Item to Purchase': [total_df['Amount of Item to Purchase'].sum()]
    })
    pd.set_option('display.float_format', '{:.2f}'.format)


    total_cost_sum = total_df['Total Cost'].sum()
    amount_to_purchase_sum = total_df['Amount of Item to Purchase'].sum()
#from here
    merged_df['QTY Defecit'] = merged_df['QTY Defecit'].apply(lambda x: 'NA' if x <= 0 else x)
    merged_df['Amount of Item to Purchase'] = merged_df['Amount of Item to Purchase'].apply(lambda x: 'NA' if x <= 0 else x)
    merged_df.loc[merged_df['rate'] == 0, 'Amount of Item to Purchase'] = 'Not Found'
#to here
    merged_df = merged_df.rename(columns={
    'item_name': 'Item Name',
    'item_code': 'Item Code',
    'qty': 'Quantity',
    'total': 'Total',
    'rate': 'Rate'
    })
    merged_df.reset_index(drop=True, inplace=True)
    merged_html = merged_df.to_html(index=False, header=True)

    if request.args.get('download') == 'excel':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            merged_df.to_excel(writer, index=False, sheet_name='Merged Data')
        
        output.seek(0)

        filename = f"PENDING {item} .xlsx"  

        return send_file(output, as_attachment=True, download_name=filename, 
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    return render_template('display.html', item=item, qty=qty, table=merged_html,
                        total_cost_sum=total_cost_sum, amount_to_purchase_sum=amount_to_purchase_sum)

import io

   
from flask import send_file
from io import BytesIO

# Function to download data as Excel
@app.route('/download_excel', methods=['GET'])
def download_excel():
    bom_name = request.args.get('bom_name')
    quantity = float(request.args.get('quantity', 1))  # Default quantity is 1

    if not bom_name:
        return jsonify({'error': 'BOM name is required'}), 400

    try:
        # Fetch result_df and bom_filtered_df similar to the '/search' route
        result_df = get_result_df()

        base_url = 'https://erpv14.electrolabgroup.com/'
        endpoint = 'api/resource/BOM'
        url = base_url + endpoint
        headers = {
            'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'
        }
        params = {
            'fields': '["name","item","items.item_name","items.item_code","items.qty"]',
            'limit_start': 0,
            'limit_page_length': 100000000000,
            'filters': '[["is_default", "=", 1]]'
        }

        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        bom_df = pd.DataFrame(data['data'])

        bom_filtered_df = bom_df[bom_df['item'] == bom_name]

        # Merge BOM data with result_df
        final_df = pd.merge(bom_filtered_df, result_df, on=['item_code'], how='left')
        final_df = final_df.fillna(0)
        final_df['qty'] = (final_df['qty'] * quantity).astype(int)
        final_df = final_df.rename(columns={
         'so_pending_qty': 'Subcontracting Order Pending Quantity (1)',
        'stock_mahape_qc': 'Stock Mahape & QC (4) [ 2 + 3]',
        'total': 'Total [1 +4 +5]',
        'pending_qty': 'Pending Quantity (5)',
        'qualitycontrol_quantity': 'Quality Control Quantity (3)',
        'mahape_quantity': 'Mahape Quantity (2)',
        'dictionary':'Dictionary',
        'name': 'BOM Name' 
        })
        new_column_order = [
        'BOM Name',  
        'item',
        'item_name',
        'item_code',
        'qty',
        'Dictionary',  
        'Subcontracting Order Pending Quantity (1)',
        'Mahape Quantity (2)',
        'Quality Control Quantity (3)',
        'Stock Mahape & QC (4) [ 2 + 3]',
        'Pending Quantity (5)',
        'Total [1 +4 +5]'
    ]

        final_df = final_df[new_column_order]


        # Additional tables processing
        additional_tables = []
        all_item_codes = list(bom_filtered_df['item_name'].unique())
        iteration = 1
        max_iterations = 10
        next_item_codes = set()

        while all_item_codes and iteration <= max_iterations:
            for item_code in all_item_codes:
                additional_data_df = bom_df[bom_df['item'] == item_code]
                if not additional_data_df.empty:
                    additional_table_df = pd.merge(additional_data_df, result_df, on=['item_code'], how='left')
                    additional_table_df = additional_table_df.fillna(0)
                    additional_table_df['qty'] = (additional_table_df['qty'] * quantity).astype(int)
                    additional_table_df['item'] = item_code
                    additional_tables.append((item_code, additional_table_df))

                    next_item_codes.update(additional_data_df['item_name'].unique())

            all_item_codes = list(next_item_codes)
            iteration += 1

#for all
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write the main data to the first sheet
            final_df.to_excel(writer, sheet_name='Main Data', index=False)

            # Write each additional table to a separate sheet
            for sheet_name, table_df in additional_tables:
                safe_sheet_name = sanitize_sheet_name(sheet_name)
                table_df.to_excel(writer, sheet_name=safe_sheet_name[:31], index=False)  # Excel sheet names must be <= 31 chars

        output.seek(0)

        # Send the Excel file as a downloadable response
        return send_file(output, as_attachment=True, download_name=f'{bom_name}_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def sanitize_sheet_name(sheet_name):
    return re.sub(r'[\\/:"*?<>|]', '_', sheet_name)[:31]

from flask import Flask, render_template, request, jsonify
import psycopg2

# Database connection function
def get_db_connection():
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='postgres',  # Use your database name
        user='postgres',  # Replace with your PostgreSQL username
        password='admin@123'
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/suggest', methods=['GET'])
def suggest():
    query = request.args.get('query', '')
    suggestions = []

    # Fetch suggestions from the database
    if query:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT item FROM item WHERE item ILIKE %s LIMIT 10", ('%' + query + '%',))  # Use ILIKE for case-insensitive search
        suggestions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

    return jsonify(suggestions)

if __name__ == '__main__':
    app.run(debug=True)
