import sqlite3

conn = sqlite3.connect('iot_data.db')
cursor = conn.cursor()

# Check tables
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables:', tables)

# Check sensor data
cursor.execute('SELECT COUNT(*) FROM sensor_data')
sensor_count = cursor.fetchone()[0]
print(f'Sensor data rows: {sensor_count}')

if sensor_count > 0:
    cursor.execute('SELECT * FROM sensor_data LIMIT 5')
    print('Sample sensor data:', cursor.fetchall())

# Check device status
cursor.execute('SELECT COUNT(*) FROM device_status')
status_count = cursor.fetchone()[0]
print(f'Device status rows: {status_count}')

if status_count > 0:
    cursor.execute('SELECT * FROM device_status LIMIT 5')
    print('Sample device status:', cursor.fetchall())

conn.close()
