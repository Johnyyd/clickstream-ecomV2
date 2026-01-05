"""Check if Spark/Java paths exist"""
import os

paths = {
    "JAVA_HOME": r"C:\LUUDULIEU\APP\JDK\jdk-17.0.12",
    "SPARK_HOME": r"C:\LUUDULIEU\APP\Spark\spark-3.5.7",
    "HADOOP_HOME": r"C:\LUUDULIEU\APP\Hadoop\hadoop-3.3.5\hadoop-3.3.5",
    "Python (venv)": r"C:\LUUDULIEU\CODE\github\clickstream-ecomV2\.venv\Scripts\python.exe",
}

print("Checking paths...\n")
for name, path in paths.items():
    exists = os.path.exists(path)
    status = "✓ OK" if exists else "❌ NOT FOUND"
    print(f"{name:20} {status}")
    print(f"  {path}")
    print()

# Check for java.exe
java_bin = os.path.join(paths["JAVA_HOME"], "bin", "java.exe")
if os.path.exists(java_bin):
    print(f"✓ Java executable found: {java_bin}")
else:
    print(f"❌ Java executable NOT found: {java_bin}")
    
# Check JAVA_HOME environment variable
env_java = os.environ.get("JAVA_HOME")
print(f"\nCurrent JAVA_HOME env: {env_java}")
