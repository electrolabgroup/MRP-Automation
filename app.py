from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pandas as pd
import requests
import re
import os
import numpy as np

app = Flask(__name__)
app.secret_key = os.urandom(24)

import pandas as pd
import psycopg2

def get_result_df():
    conn = psycopg2.connect(
        host='192.168.2.11',
        port=5432,
        database='postgres',
        user='postgres',  
        password='admin@123'
    )
    
    query = "SELECT * FROM result_df"
    df = pd.read_sql(query, conn)
    
    conn.close()
    
    df['dictionary'] = df['dictionary'].fillna('')    
    if 'id' in df.columns:
        df = df.drop(columns=['id'])
    
    return df


@app.route('/search', methods=['GET'])
def search():
    bom_name = request.args.get('bom_name')
    quantity = int(request.args.get('quantity')) 
    session['item'] = bom_name
    session['qty'] = quantity

    if not bom_name:
        error_message = "BOM name is incorrect X."
        return render_template('index.html', error_message=error_message)
    try:
        result_df = get_result_df()
    except Exception as e:
        error_message = str(e)
        return render_template('index.html', error_message=error_message)
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

    bom_filtered_df = bom_df[bom_df['item'] == bom_name]
    if bom_filtered_df.empty:
        error_message = "BOM name is incorrect."
        return render_template('index.html', error_message=error_message)

    final_df = pd.merge(bom_filtered_df, result_df, on=['item_code'], how='left')
    final_df = final_df.fillna(0)
    final_df['qty'] = (final_df['qty'] * quantity)

    decimal_columns = [
        'qty',
        'so_pending_qty',
        'mahape_quantity',
        'qualitycontrol_quantity',
        'stock_mahape_qc',
        'pending_qty',
        'total'
    ]

    for col in decimal_columns:
        final_df[col] = final_df[col].astype(float)

    final_df[decimal_columns] = final_df[decimal_columns].round(3)

    def rename_and_order_columns(df):
        df = df.rename(columns={
            'so_pending_qty': '*SO Pending Quantity',
            'stock_mahape_qc': 'Stock Mahape and QC',
            'total': 'Available Quantity',
            'pending_qty': 'Pending Quantity',
            'qualitycontrol_quantity': 'Quality Control Quantity',
            'mahape_quantity': 'Mahape Quantity',
            'name': 'BOM Name',
            'dictionary':'*SO to Supplier',
            'item_name': 'Item Name',
            'item_code': 'Item Code',
            'item': 'Item',
            'qty': 'Quantity',
        })
        new_column_order = [ 
            'BOM Name',  
            'Item',
            'Item Name',
            'Item Code',
            'Quantity',
            '*SO to Supplier', 
            '*SO Pending Quantity',
            'Mahape Quantity',
            'Quality Control Quantity',
            'Stock Mahape and QC',
            'Pending Quantity',
            'Available Quantity'
        ]
        return df[new_column_order]

    final_df = rename_and_order_columns(final_df)

    def color_rows(row):
        color = 'background-color: #80ed99;' if row['Quantity'] <= row['Available Quantity'] else 'background-color: #f29a9a;'
        return [color] * len(row)

    styled_df = final_df.style.apply(color_rows, axis=1).set_table_attributes('class="table table-striped"')

    styled_df = styled_df.format({
        'Quantity':'{:.3f}',
        '*SO Pending Quantity': '{:.3f}',
        'Mahape Quantity': '{:.3f}',
        'Quality Control Quantity': '{:.3f}',
        'Stock Mahape and QC': '{:.3f}',
        'Pending Quantity': '{:.3f}',
        'Available Quantity': '{:.3f}',
    })
    
    result_html = styled_df.to_html(index=False)
    custom_number_row = ['', 1, 2, 3, 4, 5, 6, 7, 8, 9, '10 (8 + 9)', 11, '12(7+10)']
    def generate_table_html(styled_df, number_row):
        result_html = styled_df.to_html(index=False)

        num_header_row = '<tr>' + ''.join(f'<th>{num}</th>' for num in number_row) + '</tr>'
        
        result_html = result_html.replace('<thead>', f'<thead>{num_header_row}')

        return result_html

    result_html = generate_table_html(styled_df, custom_number_row)

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
                additional_table_df['qty'] = (additional_table_df['qty'] * quantity)

                # Replace item column with item_code
                additional_table_df['item'] = item_code

                additional_table_df = rename_and_order_columns(additional_table_df)

                item_name = additional_data_df['name'].iloc[0]
                item_names.add(item_name)

                styled_additional_table_df = additional_table_df.style.apply(color_rows, axis=1).set_table_attributes('class="table table-striped"')
                styled_additional_table_df = styled_additional_table_df.format({
                    'Quantity':'{:.3f}',
                    '*SO Pending Quantity': '{:.3f}',
                    'Mahape Quantity': '{:.3f}',
                    'Quality Control Quantity': '{:.3f}',
                    'Stock Mahape and QC': '{:.3f}',
                    'Pending Quantity': '{:.3f}',
                    'Available Quantity': '{:.3f}',
                })

                # Generate the additional table HTML with the custom number row
                additional_table_html = generate_table_html(styled_additional_table_df, custom_number_row)

                iteration_tables_html += f'<div class="additional-table" data-name="{item_name}"><h4>Data for {item_name}</h4>{additional_table_html}</div>'

                next_item_codes.update(additional_data_df['item_name'].unique())


        if not iteration_tables_html:
            break  

        additional_tables_html += iteration_tables_html
        all_item_codes = list(next_item_codes)  
        iteration += 1

    if iteration > max_iterations:
        additional_tables_html += '<p>*</p>'

    names = sorted(list(item_names))

    return render_template('result.html', table=result_html, additional_tables=additional_tables_html, names=names, item=bom_name,qty=quantity)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for


@app.route('/display', methods=['GET'])
def display():
    item = session.get('item')
    qty = session.get('qty')

    if not item or qty is None:
        return redirect(url_for('search'))  # Redirect to search if no data

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

#this is optional - magar me to karunga
    total_cost_sum = f"{total_cost_sum:.3f}"
    amount_to_purchase_sum = f"{amount_to_purchase_sum:.3f}"
#from here
    merged_df['QTY Defecit'] = merged_df['QTY Defecit'].apply(lambda x: 'NA' if x <= 0 else x)
    merged_df['Amount of Item to Purchase'] = merged_df['Amount of Item to Purchase'].apply(lambda x: 'NA' if x <= 0 else x)
    merged_df.loc[merged_df['rate'] == 0, 'Amount of Item to Purchase'] = 'Not Found'
#to here
    merged_df = merged_df.rename(columns={
    'item_name': 'Item Name',
    'item_code': 'Item Code',
    'qty': 'Quantity',
    'total': 'Available Quantity',
    'rate': 'Rate'
    })
    merged_df.reset_index(drop=True, inplace=True)
    merged_html = merged_df.to_html(index=False, header=True)

    if request.args.get('download') == 'excel':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            merged_df.to_excel(writer, index=False, sheet_name='Merged Data')
        
        output.seek(0)

        filename = f"Costing from PR {item} .xlsx"  

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
        final_df['qty'] = (final_df['qty'] * quantity)
        final_df = final_df.rename(columns={
            'so_pending_qty': '*SO Pending Quantity',
            'stock_mahape_qc': 'Stock Mahape and QC',
            'total': 'Available Quantity',
            'pending_qty': 'Pending Quantity',
            'qualitycontrol_quantity': 'Quality Control Quantity',
            'mahape_quantity': 'Mahape Quantity',
            'name': 'BOM Name',
            'dictionary': '*SO to Supplier'
        })
        new_column_order = [
            'BOM Name',  
            'item',
            'item_name',
            'item_code',
            'qty',
            '*SO to Supplier', 
            '*SO Pending Quantity',
            'Mahape Quantity',
            'Quality Control Quantity',
            'Stock Mahape and QC',
            'Pending Quantity',
            'Available Quantity'
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
                    additional_table_df['qty'] = (additional_table_df['qty'] * quantity)
                    additional_table_df['item'] = item_code

                    # Apply renaming and column order to additional tables
                    additional_table_df = additional_table_df.rename(columns={
                        'so_pending_qty': '*SO Pending Quantity',
                        'stock_mahape_qc': 'Stock Mahape and QC',
                        'total': 'Available Quantity',
                        'pending_qty': 'Pending Quantity',
                        'qualitycontrol_quantity': 'Quality Control Quantity',
                        'mahape_quantity': 'Mahape Quantity',
                        'name': 'BOM Name',
                        'dictionary': '*SO to Supplier'
                    })
                    additional_table_df = additional_table_df[new_column_order]

                    additional_tables.append((item_code, additional_table_df))
                    next_item_codes.update(additional_data_df['item_name'].unique())

            all_item_codes = list(next_item_codes)
            iteration += 1

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

@app.route('/download_filtered_excel', methods=['GET'])
def download_filtered_excel():
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
        final_df['qty'] = final_df['qty'].astype(float)
        final_df['total'] = final_df['total'].astype(float)
        final_df['qty'] = (final_df['qty'] * quantity)
        final_df = final_df.rename(columns={
            'so_pending_qty': '*SO Pending Quantity',
            'stock_mahape_qc': 'Stock Mahape and QC',
            'pending_qty': 'Pending Quantity',
            'qualitycontrol_quantity': 'Quality Control Quantity',
            'mahape_quantity': 'Mahape Quantity',
            'name': 'BOM Name',
            'dictionary':'*SO to Supplier',
            'total':'Available Quantity'
        })
        new_column_order = [
            'BOM Name',  
            'item',
            'item_name',
            'item_code',
            'qty',
            '*SO to Supplier', 
            '*SO Pending Quantity',
            'Mahape Quantity',
            'Quality Control Quantity',
            'Stock Mahape and QC',
            'Pending Quantity',
            'Available Quantity']

        final_df = final_df[new_column_order]

        filtered_df = final_df[final_df['qty'] > final_df['Available Quantity']]

        # Prepare for additional tables
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
                    additional_table_df['qty'] = additional_table_df['qty'].astype(float)
                    additional_table_df['total'] = additional_table_df['total'].astype(float)
                    additional_table_df['qty'] = (additional_table_df['qty'] * quantity)
                    additional_table_df['item'] = item_code

                    # Filter the additional table for rows where qty > Total
                    filtered_additional_table_df = additional_table_df[additional_table_df['qty'] > additional_table_df['total']]
                    
                    if not filtered_additional_table_df.empty:  # Only add if there are rows that match the condition
                        # Apply the same renaming logic to additional tables
                        filtered_additional_table_df = filtered_additional_table_df.rename(columns={
                            'so_pending_qty': '*SO Pending Quantity',
                            'stock_mahape_qc': 'Stock Mahape and QC',
                            'pending_qty': 'Pending Quantity',
                            'qualitycontrol_quantity': 'Quality Control Quantity',
                            'mahape_quantity': 'Mahape Quantity',
                            'name': 'BOM Name',
                            'dictionary': '*SO to Supplier',
                            'total':'Available Quantity'
                        })

                        # Ensure consistent column order
                        filtered_additional_table_df = filtered_additional_table_df[new_column_order]

                        additional_tables.append((item_code, filtered_additional_table_df))

                    next_item_codes.update(additional_data_df['item_name'].unique())

            all_item_codes = list(next_item_codes)
            iteration += 1

        # Create an Excel file with both the filtered data and additional tables
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write the filtered data to the first sheet
            filtered_df.to_excel(writer, sheet_name='Main Data', index=False)

            # Write each additional table to a separate sheet
            for sheet_name, table_df in additional_tables:
                safe_sheet_name = sanitize_sheet_name(sheet_name)
                table_df.to_excel(writer, sheet_name=safe_sheet_name[:31], index=False)  # Excel sheet names must be <= 31 chars

        output.seek(0)

        return send_file(output, as_attachment=True, download_name=f'STOCK OUT {bom_name}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        return jsonify({'error': str(e)}), 500

from flask import Flask, render_template, request, jsonify
import psycopg2

# Database connection function
def get_db_connection():
    return psycopg2.connect(
        host='192.168.2.11',
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

    if query:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT item FROM item WHERE item ILIKE %s LIMIT 10", ('%' + query + '%',))  
        suggestions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

    return jsonify(suggestions)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7410)