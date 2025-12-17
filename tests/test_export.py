from data_storage import DataStorage
from analytics import IoTAnalytics

# Test the export functionality
storage = DataStorage("iot_data.db")
analytics = IoTAnalytics(storage)

print("Testing export functionality...")

# Test CSV export for temp_sensor_01
print("\n1. Testing CSV export for temp_sensor_01...")
csv_data = analytics.export_sensor_data_csv('temp_sensor_01', 'temperature', 24)
print(f"CSV buffer size: {len(csv_data.getvalue())} bytes")
csv_data.seek(0)
print("First 200 characters:")
print(csv_data.read(200).decode('utf-8'))

# Test Excel export
print("\n2. Testing Excel export for temp_sensor_01...")
excel_data = analytics.export_device_report_excel('temp_sensor_01', 24)
print(f"Excel buffer size: {len(excel_data.getvalue())} bytes")

# Test performance report
print("\n3. Testing performance report...")
report = analytics.generate_performance_report(24)
print(f"Performance report keys: {list(report.keys())}")
if report:
    print(f"Summary: {report.get('summary', {})}")

print("\nExport test completed!")
