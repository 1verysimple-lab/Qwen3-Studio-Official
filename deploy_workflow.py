"""
Complete Deployment Workflow for Qwen3 Studio

This script guides you through the entire deployment process.
Run this after making changes to your application.
"""
import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def print_step(number, text):
    """Print a step number."""
    print(f"\n{'─' * 70}")
    print(f"STEP {number}: {text}")
    print('─' * 70 + "\n")

def run_command(description, command):
    """Run a command and show the output."""
    print(f"▶ {description}")
    print(f"  Command: {command}\n")
    
    result = subprocess.run(command, shell=True)
    
    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}")
        return False
    
    print(f"\n✅ {description} - Complete")
    return True

def check_file_exists(filepath, description):
    """Check if a file exists and show its size."""
    path = Path(filepath)
    if path.exists():
        size_mb = path.stat().st_size / (1024**2)
        size_gb = path.stat().st_size / (1024**3)
        
        if size_gb >= 1:
            print(f"✅ {description}: {size_gb:.2f} GB")
        else:
            print(f"✅ {description}: {size_mb:.1f} MB")
        return True
    else:
        print(f"❌ {description} not found at: {filepath}")
        return False

def main():
    print_header("QWEN3 STUDIO - COMPLETE DEPLOYMENT WORKFLOW")
    
    print("This script will guide you through:")
    print("  1. Building the application bundle (2-3 GB)")
    print("  2. Uploading to HuggingFace")
    print("  3. Building the tiny installer (5-10 MB)")
    print("  4. Instructions for GitHub upload")
    
    print("\n⚠️  PREREQUISITES:")
    print("  ✓ PyInstaller installed (pip install pyinstaller)")
    print("  ✓ huggingface_hub installed (pip install huggingface_hub)")
    print("  ✓ All your code changes committed")
    print("  ✓ pq.ico file in current directory")
    
    response = input("\nReady to proceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Deployment cancelled.")
        return
    
    # =====================================================================
    # STEP 1: Build Application Bundle
    # =====================================================================
    print_step(1, "Build Application Bundle")
    
    print("This will create a ~2-3 GB zip file containing your entire application.")
    print("This includes:")
    print("  • All Python dependencies")
    print("  • Your modules (plugins)")
    print("  • Your tutorials")
    print("  • SoX audio processor")
    print("  • Everything except the AI engine")
    
    response = input("\nBuild application bundle? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Skipping build...")
    else:
        if not run_command("Building application bundle", "python build_app_bundle.py"):
            print("\n❌ Build failed. Please fix errors and try again.")
            return
        
        # Verify the build
        if not check_file_exists("dist/Qwen_Studio_App.zip", "Application bundle"):
            print("\n❌ Build completed but zip file not found!")
            return
    
    # =====================================================================
    # STEP 2: Upload to HuggingFace
    # =====================================================================
    print_step(2, "Upload Application to HuggingFace")
    
    print("This will upload your 2-3 GB application to HuggingFace.")
    print("⏳ Upload time depends on your internet speed:")
    print("   • 10 Mbps upload: ~45 minutes for 3 GB")
    print("   • 20 Mbps upload: ~25 minutes for 3 GB")
    print("   • 50 Mbps upload: ~10 minutes for 3 GB")
    
    if not check_file_exists("dist/Qwen_Studio_App.zip", "Application bundle"):
        print("\n❌ No zip file to upload. Build it first.")
        return
    
    response = input("\nUpload to HuggingFace now? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Skipping upload...")
        print("\n⚠️  Remember to upload manually later with:")
        print("   python upload_app_to_hf.py")
    else:
        if not run_command("Uploading to HuggingFace", "python upload_app_to_hf.py"):
            print("\n❌ Upload failed. Check your internet connection and HF token.")
            return
    
    # =====================================================================
    # STEP 3: Build Tiny Installer
    # =====================================================================
    print_step(3, "Build Tiny Installer")
    
    print("This will create a ~5-10 MB installer executable.")
    print("This installer will:")
    print("  • Download the app from HuggingFace")
    print("  • Download the engine from HuggingFace")
    print("  • Install everything")
    print("  • Create desktop shortcut")
    
    response = input("\nBuild installer? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Skipping installer build...")
    else:
        if not run_command("Building installer", "python build_installer.py"):
            print("\n❌ Installer build failed.")
            return
        
        if not check_file_exists("dist/Qwen3_Studio_Setup.exe", "Installer"):
            print("\n❌ Build completed but installer not found!")
            return
    
    # =====================================================================
    # STEP 4: GitHub Upload Instructions
    # =====================================================================
    print_step(4, "Upload Installer to GitHub")
    
    print("🎯 MANUAL STEP REQUIRED:")
    print("\n1. Go to your GitHub repository")
    print("   https://github.com/YOUR_USERNAME/Qwen3-Studio/releases")
    
    print("\n2. Click 'Create a new release'")
    
    print("\n3. Fill in:")
    print("   Tag: v4.1.0")
    print("   Title: Qwen3 Studio v4.1.0")
    
    print("\n4. Upload this file:")
    print("   📁 dist/Qwen3_Studio_Setup.exe")
    
    print("\n5. Add release notes (see HUGGINGFACE_DEPLOYMENT.md for template)")
    
    print("\n6. Click 'Publish release'")
    
    print("\n7. Update your README with download link:")
    print("   [Download](https://github.com/YOUR_USERNAME/Qwen3-Studio/releases/latest)")
    
    # =====================================================================
    # SUMMARY
    # =====================================================================
    print_header("DEPLOYMENT COMPLETE!")
    
    print("📋 Summary of what you deployed:\n")
    
    print("HuggingFace (Bluesed/QWEN_STUDIO):")
    if check_file_exists("dist/Qwen_Studio_App.zip", "  • Application"):
        pass
    print("  • Engine (already there)")
    
    print("\nGitHub (YOUR_REPO/releases):")
    if check_file_exists("dist/Qwen3_Studio_Setup.exe", "  • Installer"):
        pass
    
    print("\n🎉 Users can now:")
    print("  1. Download Qwen3_Studio_Setup.exe from GitHub")
    print("  2. Run it")
    print("  3. Installer automatically downloads everything from HuggingFace")
    print("  4. Application is installed and ready!")
    
    print("\n📊 Total downloads per user:")
    print("  • Installer: 5-10 MB (from GitHub)")
    print("  • Application: 2-3 GB (auto from HuggingFace)")
    print("  • Engine: 10 GB (auto from HuggingFace)")
    print("  • Total: ~13 GB")
    
    print("\n✅ Everything hosted properly:")
    print("  ✓ Tiny installer on GitHub (under 100 MB limit)")
    print("  ✓ Large files on HuggingFace (no size limits)")
    print("  ✓ Professional installation experience")
    
    print("\n" + "=" * 70)
    print("🚀 Deployment workflow complete!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Deployment cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
