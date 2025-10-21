"""Check Python environment and PySpark installation"""
import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Virtual env: {sys.prefix}")
print()

# Check if in venv
in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
print(f"Running in virtual environment: {in_venv}")
print()

# Try importing PySpark
try:
    import pyspark
    print(f"✓ PySpark version: {pyspark.__version__}")
    print(f"  Location: {pyspark.__file__}")
except ImportError as e:
    print(f"❌ PySpark not found: {e}")

# Check Java
java_home = os.environ.get("JAVA_HOME")
print(f"\nJAVA_HOME: {java_home}")
if java_home:
    java_exe = os.path.join(java_home, "bin", "java.exe")
    print(f"Java executable exists: {os.path.exists(java_exe)}")
