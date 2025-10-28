"""Test Spark initialization"""
import os
import sys

print("=" * 60)
print("TESTING SPARK INITIALIZATION")
print("=" * 60)

# Check JAVA_HOME
print(f"\n1. JAVA_HOME: {os.environ.get('JAVA_HOME', 'NOT SET')}")

# Check Java executable
java_exe = os.path.join(os.environ.get('JAVA_HOME', ''), 'bin', 'java.exe')
print(f"2. Java exe: {java_exe}")
print(f"3. Java exists: {os.path.exists(java_exe)}")

# Try importing Spark
print("\n4. Importing Spark session...")
try:
    from app.spark.session import get_spark_session
    print("   ✅ Import successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try creating session
print("\n5. Creating Spark session...")
try:
    spark = get_spark_session()
    if spark:
        print(f"   ✅ Spark session created: version {spark.version}")
    else:
        print("   ❌ Spark session is None")
except Exception as e:
    print(f"   ❌ Session creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("SPARK TEST COMPLETE")
print("=" * 60)
