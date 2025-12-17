import io
from telegram import InputFile

# Test if InputFile works with our export data
from data_storage import DataStorage
from analytics import IoTAnalytics

storage = DataStorage("iot_data.db")
analytics = IoTAnalytics(storage)

print("Testing InputFile creation...")

# Test CSV export
csv_buffer = analytics.export_sensor_data_csv('temp_sensor_01', 'temperature', 24)
print(f"CSV buffer size: {len(csv_buffer.getvalue())} bytes")

# Test InputFile creation
try:
    input_file = InputFile(csv_buffer, filename="test_temp_sensor_01.csv")
    print("✅ InputFile created successfully")
    print(f"InputFile filename: {input_file.filename}")
except Exception as e:
    print(f"❌ InputFile creation failed: {e}")

# Test Excel export
excel_buffer = analytics.export_device_report_excel('temp_sensor_01', 24)
print(f"Excel buffer size: {len(excel_buffer.getvalue())} bytes")

try:
    input_file_excel = InputFile(excel_buffer, filename="test_temp_sensor_01.xlsx")
    print("✅ Excel InputFile created successfully")
    print(f"Excel InputFile filename: {input_file_excel.filename}")
except Exception as e:
    print(f"❌ Excel InputFile creation failed: {e}")

print("Test completed!")
