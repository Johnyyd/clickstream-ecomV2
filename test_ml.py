"""Test ML functions directly"""
print("Testing ML import...")
try:
    from spark_ml import ml_user_segmentation_kmeans
    print("✓ Import successful")
    
    print("\nTesting K-Means execution...")
    result = ml_user_segmentation_kmeans()
    print("✓ Execution successful")
    print(f"Result type: {type(result)}")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
    
    if isinstance(result, dict):
        if "error" in result:
            print(f"❌ Error in result: {result['error']}")
        else:
            print(f"✓ Success! Algorithm: {result.get('algorithm', 'N/A')}")
            
except Exception as e:
    print(f"❌ Exception: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
