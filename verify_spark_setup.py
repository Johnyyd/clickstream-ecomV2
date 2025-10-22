"""
Verify Spark/Java Setup
Check if Java is properly installed and configured for Spark
"""
import os
import sys
import subprocess

def check_java():
    """Check if Java is installed and accessible"""
    print("=" * 60)
    print("🔍 CHECKING JAVA SETUP")
    print("=" * 60)
    
    # Check JAVA_HOME environment variable
    java_home = os.environ.get("JAVA_HOME")
    print(f"\n1. JAVA_HOME environment variable:")
    if java_home:
        print(f"   ✅ Set to: {java_home}")
        
        # Check if path exists
        if os.path.exists(java_home):
            print(f"   ✅ Path exists")
            
            # Check for java.exe
            java_exe = os.path.join(java_home, "bin", "java.exe")
            if os.path.exists(java_exe):
                print(f"   ✅ java.exe found: {java_exe}")
            else:
                print(f"   ❌ java.exe NOT found at: {java_exe}")
                return False
        else:
            print(f"   ❌ Path does NOT exist: {java_home}")
            return False
    else:
        print("   ❌ JAVA_HOME not set")
        return False
    
    # Try to run java -version
    print(f"\n2. Testing java command:")
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        java_version = result.stderr  # java -version outputs to stderr
        print(f"   ✅ Java is working!")
        print(f"   Version info:\n{java_version}")
        
        # Check if it's Java 8, 11, or 17 (recommended for Spark)
        if any(v in java_version for v in ["1.8", "11.", "17."]):
            print(f"   ✅ Java version is compatible with Spark")
        else:
            print(f"   ⚠️  Java version might not be optimal for Spark (recommend Java 8, 11, or 17)")
        
        return True
        
    except FileNotFoundError:
        print(f"   ❌ 'java' command not found in PATH")
        print(f"   💡 Add {java_home}\\bin to your PATH environment variable")
        return False
    except subprocess.TimeoutExpired:
        print(f"   ❌ java command timed out")
        return False
    except Exception as e:
        print(f"   ❌ Error running java: {e}")
        return False


def check_spark_session():
    """Try to create a Spark session"""
    print("\n" + "=" * 60)
    print("🔍 CHECKING SPARK SESSION")
    print("=" * 60)
    
    try:
        from spark_session import get_spark_session
        
        print("\n3. Attempting to create Spark session...")
        spark = get_spark_session()
        
        if spark is None:
            print("   ❌ Spark session creation failed")
            return False
        
        print(f"   ✅ Spark session created successfully!")
        print(f"   ✅ Spark version: {spark.version}")
        
        # Test simple operation
        print("\n4. Testing Spark operations...")
        try:
            test_df = spark.createDataFrame([(1, "test"), (2, "hello")], ["id", "value"])
            count = test_df.count()
            print(f"   ✅ Spark DataFrame test passed (count: {count})")
            return True
        except Exception as e:
            print(f"   ❌ Spark operation failed: {e}")
            return False
            
    except ImportError as e:
        print(f"   ❌ Cannot import spark_session: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_recommendations():
    """Print setup recommendations"""
    print("\n" + "=" * 60)
    print("💡 SETUP RECOMMENDATIONS")
    print("=" * 60)
    
    print("""
1. Install Java (if not installed):
   Download from: https://adoptium.net/
   Recommended version: Java 11 or Java 17
   
2. Set JAVA_HOME environment variable:
   - Windows: System Properties → Environment Variables
   - Add new system variable:
     Name: JAVA_HOME
     Value: C:\\Program Files\\Eclipse Adoptium\\jdk-11.0.x.x-hotspot
     (or your actual Java installation path)
   
3. Add Java to PATH:
   - Edit PATH environment variable
   - Add: %JAVA_HOME%\\bin
   
4. Update spark_session.py:
   - Open: spark_session.py
   - Line 11: Update JAVA_HOME path to match your installation
   
5. Restart your terminal/IDE after setting environment variables

6. Run this script again to verify setup
""")


def main():
    print("\n" + "🚀 " * 20)
    print("SPARK/JAVA SETUP VERIFICATION")
    print("🚀 " * 20 + "\n")
    
    java_ok = check_java()
    
    if java_ok:
        spark_ok = check_spark_session()
        
        if spark_ok:
            print("\n" + "=" * 60)
            print("✅ ALL CHECKS PASSED!")
            print("=" * 60)
            print("\nYour Spark environment is properly configured.")
            print("Analytics features should work correctly.\n")
            return True
        else:
            print("\n" + "=" * 60)
            print("⚠️  JAVA OK, BUT SPARK FAILED")
            print("=" * 60)
            print_recommendations()
            return False
    else:
        print("\n" + "=" * 60)
        print("❌ JAVA SETUP INCOMPLETE")
        print("=" * 60)
        print_recommendations()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
