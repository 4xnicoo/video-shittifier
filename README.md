# video shittifier
ruins the quality of a video. great tool for making low quality shitposts and all that stuff.

I made this in a few minutes. it has it's flaws. the code isn't great.
but feel free to make some improvements or modify it to your needs.

## Install
### Windows Install
1. Open `install.bat` to install the libraries.
2. Once libraries have been installed, run `main.py`
### Alternative Install
1. Run `pip install -r requirements.txt` in terminal
##  Usage
### Uploading a video
1. Select a valid video (must be VIDEO format, such as .mp4) in the popup when opening the program.
### Configure output
1. You will be asked to select a compression mode: percentage to compress, or target size. (respond with P/T accordingly)
2. Select the audio quality. You may input a number, or use one of the presents (h/m/l/v)
3. Depending on the compression mode you selected, you will get two different ways of compressing the file.
#### - Percentage mode
The original file size is at 100%. The percentage you input will be the percentage of the file that will remain. For example, if you input 30%, then the file will be shrunk to 30% of it's original size. If you input 90%, then it will only lose 10% of quality.
#### - Target mode
Input the desired compressed file size in MB. The program will give you the current size in MB, KB and bytes for reference.
If compression to the desired file size is not possible, the program will attempt to get as close as possible to it. You will be alerted in the compression results if the compression to the file size was unsuccessful.
### Recursive compression
If you are using the percentage compression mode, you will have the option to recursively compress the video. After a compression has finished, you can type 'Y' to compress the output video again, by either reusing the settings or inputting new ones. 
