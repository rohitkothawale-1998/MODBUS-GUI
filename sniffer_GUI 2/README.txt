SVN directory:
http://w12svnprodboc.nam.gad.schneider-electric.com/mpc/scratch/sniffer_GUI

0. Download the sniffer_GUI source from SVN, get into the scratch\sniffer_GUI\Python_Libraries find the needed files.

1. Use the included Win64 Redis Installer (redis-2.4.6-setup-64-bit.exe) included in the \Python_Libraries directory, install it to your windows 
system, and your OS would automatic promote it into a service and keep it running.


Then, 
2. Install python27, and other libs: PySerial, wxPython. (you can skip this if you've got the seWSNview.py already working).

3. Install the pip by running >python get-pip.py (get-pip.py script is included in the Python_Libraries directory)

4. Find the VCForPython27.exe in the same directory, 
Install this to solve any problem related to compile Python stuff with VC++ pre-requisite. Otherwise, on most of the freshly installed OS, 
doing pip install in the new step (step#5) you will encounter a lot of compilation errors.


5. Use Pip to install the following:
   a. >pip install redis
   b. >pip install numpy scipy python-matplotlib
(Now you should have no problem to run the seWSNView.py with Redis support)

6. Install numpy, matplotlib using pip
>pip install numpy matplotlib

7. Run 
>python wdt_plot_client.py temp humid
Before you run this, please make sure two things:
a. you need to run the seWSNView.py for a little while to collect enough data points into the redis DB.
b. you need to edit this file (wdt_plot_client.py) at line#326 to put in your sensors MAC list.