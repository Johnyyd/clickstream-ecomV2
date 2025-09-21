from db import events_col
from pprint import pprint

# Đếm số lượng events
count = events_col().count_documents({})
print(f"\nTotal events in database: {count}")

# Xem mẫu 3 events đầu tiên
if count > 0:
    print("\nSample events:")
    for event in events_col().find().limit(3):
        pprint(event)