import psycopg2
from termcolor import cprint
from core.env_variables import PSQL_CREDENTIALS
from core.key_definition import DBTableColumns

def get_table_columns(table) -> list:
    match table.split('.')[1]:
        case 'k_line':
            return DBTableColumns.k_line

        case 'order_record':
            return DBTableColumns.order_record

        case 'acc_status':
            return DBTableColumns.acc_status


def read_last_record(table,record_size=1) -> list:
        conn   = psycopg2.connect(**PSQL_CREDENTIALS)
        cur    = conn.cursor()
        query  = f"SELECT * FROM {table} ORDER BY updated_time DESC LIMIT {record_size}"
        cur.execute(query)
        column_keys = get_table_columns(table)
        last_record = cur.fetchall()
        last_record = last_record[::-1]
        cur.close()
        conn.close()
        last_record = [list(record) for record in last_record]
        last_record = [dict(zip(column_keys, record)) for record in last_record]

        return last_record


def insert_data(table, data) -> bool:
    conn   = psycopg2.connect(**PSQL_CREDENTIALS)
    cur    = conn.cursor()
    column_keys = get_table_columns(table)
    column_str = ', '.join(column_keys)
    value_str = ', '.join(['%s' for _ in column_keys])
    query = f"INSERT INTO {table} ({column_str}) VALUES ({value_str})"
    try:
        cur.execute(query, data)
        conn.commit()
        cprint(f"inserting to: {table}", "blue")
        cprint(f"inserting data: {data}", "blue")
        cprint(f"execute result: {cur.statusmessage}", "blue")
        cur.close()
        conn.close()
        return True
    
    except Exception as e:
        cprint(f"Error: {e}", "red")
        return False