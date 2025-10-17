@echo off
title 🚀 Spark + Java Environment Setup for Windows
echo ================================================
echo  Setting up environment variables for Spark & Java
echo ================================================
echo.

:: ==== Cấu hình các đường dẫn ====
setx JAVA_HOME "C:\Program Files\Eclipse Adoptium\jdk-21.0.8.9-hotspot" /M
setx SPARK_HOME "C:\LUUDULIEU\APP\Spark\Spark\spark-4.0.0" /M
setx HADOOP_HOME "C:\LUUDULIEU\APP\Hadoop\hadoop-3.3.4" /M

echo 🔧 Updating PATH...
setx PATH "%JAVA_HOME%\bin;%SPARK_HOME%\bin;%HADOOP_HOME%\bin;%PATH%" /M

echo.
echo ✅ Environment variables updated successfully.
echo -----------------------------------------------
echo  JAVA_HOME    = %JAVA_HOME%
echo  SPARK_HOME   = %SPARK_HOME%
echo  HADOOP_HOME  = %HADOOP_HOME%
echo -----------------------------------------------
echo.
echo ⚡ Please RESTART your PowerShell or system before testing.
pause
