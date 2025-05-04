# video shittifier

import tkinter as tk
from tkinter import filedialog
import moviepy.editor as mp
import os
import time
import threading
import sys
from colorama import init, Fore, Style

init()

spinner_active = False

def spinner_animation():
    """Display a spinner animation in the console while a process is running"""
    global spinner_active
    spinner_chars = ['/', '-', '\\', '|']
    i = 0
    while spinner_active:
        sys.stdout.write(f"\r{Fore.CYAN}Compressing video... {spinner_chars[i]}{Style.RESET_ALL}")
        sys.stdout.flush()
        i = (i + 1) % len(spinner_chars)
        time.sleep(0.2)
    
    sys.stdout.write("\r" + " " * 30 + "\r")
    sys.stdout.flush()

class CustomLogger:
    """A custom logger for MoviePy that shows a spinner instead of a progress bar"""
    
    def __init__(self):
        self.spinner_thread = None
        self.last_t = 0
    
    def callback(self, t):
        """Called by MoviePy to update progress.
        We'll use this to drive our spinner animation."""
        global spinner_active
        
        if t == 0:
            spinner_active = True
            self.spinner_thread = threading.Thread(target=spinner_animation)
            self.spinner_thread.daemon = True
            self.spinner_thread.start()
        
        if t == 1.0 and spinner_active:
            spinner_active = False
            if self.spinner_thread:
                self.spinner_thread.join(timeout=1.0)
                self.spinner_thread = None
        
        self.last_t = t
        
    def __call__(self, t):
        """Required for the logger interface"""
        self.callback(t)
        
    def __enter__(self):
        """Required for context manager support"""
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        """Stop the spinner when exiting context"""
        global spinner_active
        spinner_active = False
        if self.spinner_thread:
            self.spinner_thread.join(timeout=1.0)
            self.spinner_thread = None


def select_video_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Video File",
        filetypes=[
            ("Video files", "*.mp4 *.avi *.mov *.mkv"),
            ("All files", "*.*")
        ]
    )
    return file_path


def compress_video(input_path, output_path, target_size_mb=None, percentage=None, audio_quality='medium', retry_count=0):
    valid_audio_qualities = ['high', 'medium', 'low', 'very-low']
    # Allow custom audio quality values (they start with 'custom-')
    if audio_quality not in valid_audio_qualities and not audio_quality.startswith('custom-'):
        print(f"{Fore.YELLOW}Warning: Invalid audio quality '{audio_quality}'. Defaulting to 'medium'.{Style.RESET_ALL}")
        audio_quality = 'medium'
        
    if target_size_mb is not None and target_size_mb < 0.1:
        print(f"{Fore.RED}Warning: Target size is very small ({target_size_mb:.2f} MB).{Style.RESET_ALL}")
        print(f"{Fore.RED}This may cause compression errors. Adjusting to minimum size of 0.1 MB.{Style.RESET_ALL}")
        target_size_mb = 0.1
    
    if percentage is not None:
        estimated_size = os.path.getsize(input_path) * (percentage / 100) / (1024 * 1024)
        if estimated_size < 0.1:
            print(f"{Fore.RED}Warning: Target percentage would result in a very small file ({estimated_size:.2f} MB).{Style.RESET_ALL}")
            print(f"{Fore.RED}This may cause compression errors. Consider using a higher percentage.{Style.RESET_ALL}")
    
    if os.path.exists(output_path):
        try:
            with open(output_path, 'a'):
                pass
        except PermissionError:
            if retry_count < 3:
                print(f"{Fore.YELLOW}Output file is in use or cannot be accessed. Trying with a different filename...{Style.RESET_ALL}")
                # Generate a new output path with a unique suffix
                filename, ext = os.path.splitext(output_path)
                new_output_path = f"{filename}_{retry_count+1}{ext}"
                return compress_video(input_path, new_output_path, target_size_mb, percentage, audio_quality, retry_count+1)
            else:
                raise PermissionError(f"Cannot access the output file after {retry_count} retries. Please close any applications using the file.")
    
    try:

        video = mp.VideoFileClip(input_path)

        has_audio = hasattr(video, 'audio') and video.audio is not None
        
        if not has_audio:
            print(f"{Fore.YELLOW}Note: This video does not have an audio track.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Audio compression will be skipped.{Style.RESET_ALL}")
        
        original_size = os.path.getsize(input_path) / (1024 * 1024)
        
        if percentage is not None:
            target_size_mb = original_size * (percentage / 100)
            print(f"{Fore.BLUE}Compressing to {percentage}% of original size ({target_size_mb:.2f} MB){Style.RESET_ALL}")
        else:
            # Use provided target size
            print(f"{Fore.BLUE}Compressing to target size of {target_size_mb} MB{Style.RESET_ALL}")

        duration = video.duration
        
        if audio_quality.startswith('custom-'):
            try:
                custom_percent = float(audio_quality.split('-')[1])
                audio_bitrate_ratio = custom_percent / 100
                audio_codec = 'aac'
                print(f"{Fore.BLUE}Using custom audio quality: {custom_percent}% of total bitrate{Style.RESET_ALL}")
            except (ValueError, IndexError):
                audio_bitrate_ratio = 0.15
                audio_codec = 'aac'
                print(f"{Fore.YELLOW}Error parsing custom audio quality. Using medium (15%) instead.{Style.RESET_ALL}")
        elif audio_quality == 'high':
            audio_bitrate_ratio = 0.20
            audio_codec = 'aac'
            print(f"{Fore.BLUE}Using high audio quality{Style.RESET_ALL}")
        elif audio_quality == 'medium':
            audio_bitrate_ratio = 0.15
            audio_codec = 'aac'
            print(f"{Fore.BLUE}Using medium audio quality{Style.RESET_ALL}")
        elif audio_quality == 'low':
            audio_bitrate_ratio = 0.10
            audio_codec = 'aac'
            print(f"{Fore.BLUE}Using low audio quality{Style.RESET_ALL}")
        elif audio_quality == 'very-low':
            audio_bitrate_ratio = 0.05
            audio_codec = 'aac'
            print(f"{Fore.BLUE}Using very low audio quality{Style.RESET_ALL}")
        else:
            audio_bitrate_ratio = 0.15
            audio_codec = 'aac'
            print(f"{Fore.BLUE}Using default (medium) audio quality{Style.RESET_ALL}")
        
        total_kbits = (target_size_mb * 8192)
        
        if not has_audio:
            audio_kbits = 0
            video_kbits = total_kbits
            audio_bitrate = '0k'
        else:
            audio_kbits = total_kbits * audio_bitrate_ratio
            video_kbits = total_kbits - audio_kbits
            audio_bitrate = str(max(8, int(audio_kbits / duration))) + 'k'  # Minimum 8k audio bitrate
        
        video_bitrate = str(max(10, int(video_kbits / duration))) + 'k'  # Minimum 10k video bitrate
        
        if has_audio:
            print(f"{Fore.BLUE}Video bitrate: {video_bitrate}, Audio bitrate: {audio_bitrate}{Style.RESET_ALL}")
        else:
            print(f"{Fore.BLUE}Video bitrate: {video_bitrate}, No audio stream{Style.RESET_ALL}")

        try:
            custom_progress = CustomLogger()
            
            global spinner_active
            spinner_active = True
            spinner_thread = threading.Thread(target=spinner_animation)
            spinner_thread.daemon = True
            spinner_thread.start()
            
            try:
                if has_audio:
                    video.write_videofile(
                        output_path,
                        codec='libx264',
                        audio_codec=audio_codec,
                        bitrate=video_bitrate,
                        audio_bitrate=audio_bitrate,
                        preset='medium',
                        threads=2
                    )
                else:
                    video.write_videofile(
                        output_path,
                        codec='libx264',
                        bitrate=video_bitrate,
                        preset='medium',
                        threads=2,
                        audio=False
                    )
            finally:
                spinner_active = False
                spinner_thread.join(timeout=1.0)
        except (IOError, OSError) as e:
            spinner_active = False
            if 'spinner_thread' in locals() and spinner_thread.is_alive():
                spinner_thread.join(timeout=1.0)
                
            if "Permission denied" in str(e):
                if retry_count < 3:
                    print(f"{Fore.YELLOW}Permission error when writing file. Trying with a different filename...{Style.RESET_ALL}")
                    filename, ext = os.path.splitext(output_path)
                    new_output_path = f"{filename}_alt{retry_count+1}{ext}"
                    video.close()
                    return compress_video(input_path, new_output_path, target_size_mb, percentage, audio_quality, retry_count+1)
                else:
                    video.close()
                    raise PermissionError(f"Cannot write to output file after {retry_count} retries. Please check file permissions.")
            elif "Broken pipe" in str(e):
                video.close()
                if target_size_mb < 0.5 and retry_count < 2:
                    print(f"{Fore.YELLOW}Broken pipe error. This may be due to extremely low bitrate. Trying with a higher minimum size...{Style.RESET_ALL}")
                    return compress_video(input_path, output_path, 0.5, None, audio_quality, retry_count+1)
                else:
                    print(f"{Fore.RED}Broken pipe error details: {str(e)}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}This error often occurs when the ffmpeg process is terminated unexpectedly.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}This can happen with extremely small target sizes or permission issues.{Style.RESET_ALL}")
                    raise IOError(f"Broken pipe error during compression. The target size may be too small for this video or there might be a file access issue.")
            else:
                video.close()
                raise e

        video.close()

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise IOError(f"Compression failed: Output file {output_path} is missing or empty.")

        final_size = os.path.getsize(output_path) / (1024 * 1024)
        size_change_percent = ((final_size - original_size) / original_size) * 100
        compression_ratio = ((original_size - final_size) / original_size) * 100
        
        print(f"{Fore.CYAN}Original size: {original_size:.2f} MB{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Compressed size: {final_size:.2f} MB{Style.RESET_ALL}")
        
        if final_size >= original_size:
            # Size increased
            print(f"{Fore.RED}[FAIL] Size increased by {abs(size_change_percent):.2f}%{Style.RESET_ALL}")
            print(f"{Fore.RED}Unable to compress this video further with current settings{Style.RESET_ALL}")
        elif compression_ratio < 5:
            # Minimal compression (less than 5%)
            print(f"{Fore.YELLOW}[WARN] Minimal reduction: {compression_ratio:.2f}%{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Video might be already well-compressed or using efficient codec{Style.RESET_ALL}")
        elif percentage is not None and (abs(percentage - ((final_size / original_size) * 100)) > 10):
            # Significant deviation from target percentage
            actual_percentage = (final_size / original_size) * 100
            print(f"{Fore.YELLOW}Target: {percentage:.2f}% of original size{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Actual: {actual_percentage:.2f}% of original size{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[WARN] Could not achieve exact target percentage{Style.RESET_ALL}")
        else:
            # Successful compression
            print(f"{Fore.GREEN}[SUCCESS] Reduced by {compression_ratio:.2f}%{Style.RESET_ALL}")
        
        return {
            'original_size': original_size,
            'final_size': final_size,
            'compression_ratio': compression_ratio,
            'size_increased': final_size > original_size,
            'audio_quality': audio_quality
        }

    except Exception as e:
        spinner_active = False
        if 'spinner_thread' in locals() and spinner_thread.is_alive():
            spinner_thread.join(timeout=1.0)
            
        try:
            video.close()
        except:
            pass
        
        # the error information
        if "Permission denied" in str(e):
            print(f"{Fore.RED}Error: Permission denied when trying to access or write the file.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Tips:{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}1. Make sure the file is not open in another program.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}2. Try saving to a different location where you have write permissions.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}3. Try running the program as administrator.{Style.RESET_ALL}")
        elif "Broken pipe" in str(e):
            print(f"{Fore.RED}Error: Broken pipe during compression.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Tips:{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}1. Try a higher target size or percentage.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}2. The video might be too complex to compress to such a small size.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Unexpected error during compression: {str(e)}{Style.RESET_ALL}")
        
        raise


def process_compression(input_path):
    # Generate output path
    filename, ext = os.path.splitext(input_path)
    output_path = filename + "_compressed" + ext
    
    compression_params = {}

    os.system("cls" if os.name == "nt" else "clear")
    print(f"{Fore.GREEN}Configure Output{Style.RESET_ALL}")
    compress_mode = input(f"{Fore.YELLOW}[COMPRESS MODE] Compress by percentage or target size? (P/T){Style.RESET_ALL}").upper()
    
    print(f"\n{Fore.GREEN}Audio Quality Settings{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Current audio bitrate information:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}High quality: 20% of total bitrate{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Medium quality: 15% of total bitrate{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Low quality: 10% of total bitrate{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Very low quality: 5% of total bitrate{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}Options:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}1-100: Enter a number between 1-100 to set a custom percentage{Style.RESET_ALL}")
    print(f"{Fore.CYAN}h: High quality (20%){Style.RESET_ALL}")
    print(f"{Fore.CYAN}m: Medium quality (15%){Style.RESET_ALL}")
    print(f"{Fore.CYAN}l: Low quality (10%){Style.RESET_ALL}")
    print(f"{Fore.CYAN}v: Very low quality (5%){Style.RESET_ALL}")
    
    audio_choice = input(f"{Fore.YELLOW}[AUDIO QUALITY] Enter your choice (1-100 or h/m/l/v): {Style.RESET_ALL}").lower()
    
    try:
        if audio_choice.isdigit() or (audio_choice.replace('.', '', 1).isdigit() and audio_choice.count('.') < 2):
            # Handle custom percentage
            custom_percent = float(audio_choice)
            if 1 <= custom_percent <= 100:
                audio_quality = f"custom-{custom_percent}"
                print(f"{Fore.BLUE}Using custom audio quality: {custom_percent}% of total bitrate{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Invalid percentage. Defaulting to medium quality (15%){Style.RESET_ALL}")
                audio_quality = "medium"
        else:
            # Handle preset choices
            if audio_choice == "h":
                audio_quality = "high"
            elif audio_choice == "l":
                audio_quality = "low"
            elif audio_choice == "v":
                audio_quality = "very-low"
            else:
                audio_quality = "medium"  # Default to medium if invalid or "m" chosen
    except ValueError:
        print(f"{Fore.YELLOW}Invalid input. Defaulting to medium quality (15%){Style.RESET_ALL}")
        audio_quality = "medium"
        
    print(f"{Fore.BLUE}Selected audio quality: {audio_quality}{Style.RESET_ALL}")
    
    if os.path.exists(input_path):
        size_bytes = os.path.getsize(input_path)
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        
        print(f"\n{Fore.CYAN}Current file size:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  {size_mb:.2f} MB{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  {size_kb:.2f} KB{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  {size_bytes:,} bytes{Style.RESET_ALL}\n")
    
    try:
        if compress_mode == 'P':
            # Percentage mode stuff
            try:
                percentage = float(input(f"{Fore.YELLOW}Enter target percentage (e.g., 30 for 30% of original size): {Style.RESET_ALL}"))
                if percentage <= 0 or percentage >= 100:
                    print(f"{Fore.RED}Percentage must be between 0 and 100{Style.RESET_ALL}")
                    return None
            except ValueError:
                print(f"{Fore.RED}Invalid input. Please enter a valid number.{Style.RESET_ALL}")
                return None
                
            compression_params = {'mode': 'P', 'percentage': percentage, 'audio_quality': audio_quality}
            
            # file access/perms check
            if not os.path.exists(input_path):
                print(f"{Fore.RED}Error: Input file no longer exists or cannot be accessed.{Style.RESET_ALL}")
                return None
                
            try:
                result = compress_video(input_path, output_path, percentage=percentage, audio_quality=audio_quality)
            except Exception as e:
                print(f"{Fore.RED}Compression failed: {str(e)}{Style.RESET_ALL}")
                retry = input(f"{Fore.YELLOW}Would you like to try again with different settings? (y/n): {Style.RESET_ALL}").lower()
                if retry == 'y':
                    return process_compression(input_path)
                return None
                
        elif compress_mode == 'T':
            # target size/specific size mode
            try:
                target_size = float(input(f"{Fore.YELLOW}Enter target size in MB: {Style.RESET_ALL}"))
                if target_size <= 0:
                    print(f"{Fore.RED}Target size must be greater than 0{Style.RESET_ALL}")
                    return None
            except ValueError:
                print(f"{Fore.RED}Invalid input. Please enter a valid number.{Style.RESET_ALL}")
                return None
                
            compression_params = {'mode': 'T', 'target_size': target_size, 'audio_quality': audio_quality}
            
            if not os.path.exists(input_path):
                print(f"{Fore.RED}Error: Input file no longer exists or cannot be accessed.{Style.RESET_ALL}")
                return None
                
            try:
                result = compress_video(input_path, output_path, target_size_mb=target_size, audio_quality=audio_quality)
            except Exception as e:
                print(f"{Fore.RED}Compression failed: {str(e)}{Style.RESET_ALL}")
                # Ask if user wants to try with different settings
                retry = input(f"{Fore.YELLOW}Would you like to try again with different settings? (y/n): {Style.RESET_ALL}").lower()
                if retry == 'y':
                    return process_compression(input_path)
                return None
                
        else:
            print(f"{Fore.RED}Invalid mode selected. Please use 'P' for percentage or 'T' for target size.{Style.RESET_ALL}")
            return None
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            print(f"{Fore.RED}Error: Output file was not created successfully.{Style.RESET_ALL}")
            return None
        
        # results of compression
        if not result['size_increased']:
            print(f"{Fore.GREEN}Compressed video saved to: {output_path}{Style.RESET_ALL}")
            
            # compression loop
            compress_again = input(f"\n{Fore.MAGENTA}Do you want to compress this output further? (y/n): {Style.RESET_ALL}").lower()
            if compress_again == 'y':
                reuse_settings = input(f"{Fore.MAGENTA}Reuse the same compression settings? (y/n): {Style.RESET_ALL}").lower()
                
                if reuse_settings == 'y':
                    try:
                        if compression_params['mode'] == 'P':
                            new_output = process_compression_with_params(
                                output_path, 
                                'P', 
                                percentage=compression_params['percentage'],
                                audio_quality=compression_params.get('audio_quality', 'medium')
                            )
                        else:
                            new_output = process_compression_with_params(
                                output_path, 
                                'T', 
                                target_size=compression_params['target_size'],
                                audio_quality=compression_params.get('audio_quality', 'medium')
                            )
                        return new_output
                    except Exception as e:
                        print(f"{Fore.RED}Error during further compression: {str(e)}{Style.RESET_ALL}")
                        # old settings
                        return output_path
                else:
                    # Use new settings
                    return process_compression(output_path)
        else:
            print(f"{Fore.YELLOW}Output video saved to: {output_path}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Note: Size increased rather than decreased. You may want to keep the original.{Style.RESET_ALL}")
        
        return output_path
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Compression process cancelled by user.{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}Unexpected error during compression process: {str(e)}{Style.RESET_ALL}")
        if "Permission" in str(e):
            print(f"{Fore.YELLOW}This may be a file permission issue. Try running as administrator or saving to a different location.{Style.RESET_ALL}")
        elif "not found" in str(e) or "No such file" in str(e):
            print(f"{Fore.YELLOW}The file could not be found or accessed. Check if it still exists and you have permission to access it.{Style.RESET_ALL}")
        return None


def process_compression_with_params(input_path, mode, percentage=None, target_size=None, audio_quality='medium'):
    # Generate output path
    filename, ext = os.path.splitext(input_path)
    # Remove any existing "_compressed" suffix to avoid stacking them
    # ! this might overwrite the file.
    if filename.endswith("_compressed"):
        filename = filename[:-11]
    output_path = filename + "_compressed" + ext
    
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{Fore.GREEN}Compressing with previous settings{Style.RESET_ALL}")
    
    if os.path.exists(input_path):
        size_bytes = os.path.getsize(input_path)
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        
        print(f"\n{Fore.CYAN}Current file size:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  {size_mb:.2f} MB{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  {size_kb:.2f} KB{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  {size_bytes:,} bytes{Style.RESET_ALL}\n")
    
    try:
        if mode == 'P':
            print(f"{Fore.BLUE}Reusing percentage mode: {percentage}%{Style.RESET_ALL}")
            print(f"{Fore.BLUE}Reusing audio quality: {audio_quality}{Style.RESET_ALL}")
            result = compress_video(input_path, output_path, percentage=percentage, audio_quality=audio_quality)
        else:
            print(f"{Fore.BLUE}Reusing target size mode: {target_size} MB{Style.RESET_ALL}")
            print(f"{Fore.BLUE}Reusing audio quality: {audio_quality}{Style.RESET_ALL}")
            result = compress_video(input_path, output_path, target_size_mb=target_size, audio_quality=audio_quality)
        
        if not result['size_increased']:
            print(f"{Fore.GREEN}Compressed video saved to: {output_path}{Style.RESET_ALL}")
            
            compress_again = input(f"\n{Fore.MAGENTA}Do you want to compress this output further? (y/n): {Style.RESET_ALL}").lower()
            if compress_again == 'y':
                reuse_settings = input(f"{Fore.MAGENTA}Reuse the same compression settings? (y/n): {Style.RESET_ALL}").lower()
                
                if reuse_settings == 'y':
                    if mode == 'P':
                        new_output = process_compression_with_params(output_path, 'P', percentage=percentage, audio_quality=audio_quality)
                    else:
                        new_output = process_compression_with_params(output_path, 'T', target_size=target_size, audio_quality=audio_quality)
                    return new_output
                else:
                    return process_compression(output_path)
        else:
            print(f"{Fore.YELLOW}Output video saved to: {output_path}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Note: Size increased rather than decreased. You may want to keep the original.{Style.RESET_ALL}")
        
        return output_path
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Compression process cancelled by user.{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}Unexpected error during compression process: {str(e)}{Style.RESET_ALL}")
        # Try to provide more helpful context for common errors
        if "Permission" in str(e):
            print(f"{Fore.YELLOW}This may be a file permission issue. Try running as administrator or saving to a different location.{Style.RESET_ALL}")
        elif "not found" in str(e) or "No such file" in str(e):
            print(f"{Fore.YELLOW}The file could not be found or accessed. Check if it still exists and you have permission to access it.{Style.RESET_ALL}")
        return None


def main():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        
        print(f"{Fore.YELLOW}## Video Shittifier{Style.RESET_ALL}")
        print("Please select a video to compress.")
        input_path = select_video_file()
        
        if not input_path:
            print(f"{Fore.RED}No file selected.{Style.RESET_ALL}")
            retry = input(f"{Fore.YELLOW}Would you like to select another file? (y/n): {Style.RESET_ALL}").lower()
            if retry != 'y':
                print(f"{Fore.CYAN}Goodbye!{Style.RESET_ALL}")
                break
            continue

        final_output = process_compression(input_path)
        
        if final_output:
            print(f"\n{Fore.GREEN}Output saved to: {final_output}{Style.RESET_ALL}")
            
            new_file = input(f"{Fore.MAGENTA}Do you want to compress a new file? (y/n): {Style.RESET_ALL}").lower()
            
            if new_file != 'y':
                exit_app = input(f"{Fore.MAGENTA}Exit application? (y/n to continue with latest output): {Style.RESET_ALL}").lower()
                if exit_app == 'y':
                    print(f"{Fore.CYAN}Goodbye!{Style.RESET_ALL}")
                    break
                else:
                    input_path = final_output
                    final_output = process_compression(input_path)


if __name__ == "__main__":
    main()
