"""
Cleanup Spark temporary files and directories
Run this if you encounter Spark file system errors
"""

import os
import shutil
import glob

def cleanup_spark_tmp():
    """Clean up all Spark temporary directories"""
    
    print("\n" + "="*70)
    print("🧹 CLEANING UP SPARK TEMPORARY FILES")
    print("="*70)
    
    # Directories to clean
    cleanup_dirs = [
        os.path.join(os.getcwd(), "tmp_spark"),  # Old location
        "C:/tmp/spark",  # New location
        "C:/tmp/spark-warehouse"
    ]
    
    total_freed = 0
    
    for dir_path in cleanup_dirs:
        if os.path.exists(dir_path):
            try:
                # Calculate size before deletion
                size = get_dir_size(dir_path)
                size_mb = size / (1024 * 1024)
                
                print(f"\n📁 Cleaning: {dir_path}")
                print(f"   Size: {size_mb:.2f} MB")
                
                # Remove directory
                shutil.rmtree(dir_path, ignore_errors=True)
                total_freed += size
                
                print(f"   ✅ Deleted")
                
            except Exception as e:
                print(f"   ⚠️  Error: {e}")
        else:
            print(f"\n📁 {dir_path}")
            print(f"   ℹ️  Does not exist (nothing to clean)")
    
    # Clean derby.log and metastore_db if exists
    derby_files = [
        os.path.join(os.getcwd(), "derby.log"),
        os.path.join(os.getcwd(), "metastore_db")
    ]
    
    for file_path in derby_files:
        if os.path.exists(file_path):
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"\n✅ Deleted: {file_path}")
                else:
                    shutil.rmtree(file_path, ignore_errors=True)
                    print(f"\n✅ Deleted directory: {file_path}")
            except Exception as e:
                print(f"\n⚠️  Error deleting {file_path}: {e}")
    
    print("\n" + "="*70)
    print(f"✅ CLEANUP COMPLETE")
    print(f"   Total space freed: {total_freed / (1024 * 1024):.2f} MB")
    print("="*70)
    
    # Recreate new tmp directory
    new_tmp = "C:/tmp/spark"
    os.makedirs(new_tmp, exist_ok=True)
    print(f"\n✅ Created new Spark temp directory: {new_tmp}")
    
    print("\n🔄 NEXT STEPS:")
    print("   1. Restart your Python server")
    print("   2. Try running the ML analytics again")
    print("   3. If error persists, check antivirus settings")

def get_dir_size(path):
    """Calculate total size of directory"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
    except Exception:
        pass
    return total_size

def stop_spark_sessions():
    """Stop all Spark sessions"""
    print("\n🛑 Stopping Spark sessions...")
    
    try:
        from spark_session import stop_spark_session
        stop_spark_session()
        print("✅ Spark session stopped")
    except Exception as e:
        print(f"⚠️  Could not stop Spark session: {e}")

if __name__ == "__main__":
    try:
        # Stop Spark first
        stop_spark_sessions()
        
        # Clean up
        cleanup_spark_tmp()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
