from db import analyses_col
from bson import ObjectId
from pprint import pprint

analysis_id = "68ce26be3cfb39400a65023d"
result = analyses_col().find_one({"_id": ObjectId(analysis_id)})
print("\nAnalysis Result:")
pprint(result)