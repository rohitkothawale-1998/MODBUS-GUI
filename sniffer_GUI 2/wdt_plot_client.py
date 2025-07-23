from numpy import arange, sin, pi
import matplotlib
matplotlib.use('WXAgg')

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure

import wx
import redis
import ast 
import sys
import math
RedisServer = "W7US5CB34704XSL"
#RedisServer = "10.169.104.148"

r = redis.StrictRedis(host=RedisServer, port=6379, db =0)
SCREENSIZE = 80
timeseries_label = []
data = []
colorList= ['r', 'b', 'g', 'c', 'm', 'y', 'k']
NUM_OF_COLORS = len(colorList)
sensorDef = {'temp':{'range':[0, 100], 'caption':'Temperature'},
             'humid':{'range':[0, 100], 'caption':'Humidity'},
             'rssi':{'range':[-255, 0], 'caption':'Received Signal Strength Index'},
             'battery':{'range':[0, 3.1], 'caption':'Battery'},
             'workingMemory':{'range':[0, 4000.0], 'caption':'Working Memeory Usage'},
             'deviceUptime':{'range':[0, 2000000.0], 'caption':'Device Up Time'},
             'transid':{'range':[0, 255.0], 'caption':'Transaction ID'},
             'tranid':{'range':[0, 255.0], 'caption':'Node Internal Trans ID'},
            }
setCaptions = set()
macList = []
modalities = []
              

def ADC_TempConversionSMT(f_adc):
    tempVal = 0
    iTemp = 0
    f_adc = (float(f_adc)/1000)
    tempVal1 = 34.918 * f_adc * f_adc * f_adc * f_adc * f_adc
    tempVal2 = 166.39 * f_adc * f_adc * f_adc * f_adc
    tempVal3 = 320.47 * f_adc * f_adc * f_adc
    tempVal4 = 307.7 * f_adc * f_adc
    tempVal5 = 196.92 * f_adc
    #print(f_adc, tempVal1, tempVal2, tempVal3, tempVal4, tempVal5)
    tempVal = tempVal1 - tempVal2 + tempVal3 - tempVal4 + tempVal5 - 59.212
    iTemp = ( tempVal * 10)
    tempVal = (iTemp / 10.0) #adjust to 10ths precision
    return tempVal*1.8+32

def calcHumidity(adc, temp):
    h = ((float(adc)/2047) - 0.1515) / 0.00636
    h = h / (1.0546 - 0.00216*temp)
    if h >= 95:
       h = 95
    if h < 0:
       h = 0
    return h

def printToScreen(floor, ceiling, x):
    return SCREENSIZE*float((x-floor)/(ceiling-floor))

def pick(mac, typeOfSensor):
    fulllist = r.smembers('allSensors')
    #print(fulllist)
    #print(i)
    #fullset = r.zrange(mac, 0, -1)
    #fullset = r.zrangebyscore(mac, 1429000000, "+inf")
    #fullset = r.zrange(mac, 0, -1, 'WITHSCORES') #for some reason, the "withscores" option doesn't work
    fullset = r.zrangebyscore(mac, 1448955000, "+inf")
    print(str(mac)+" ======== Totally "+ str(len(fullset))+ " data points!")
    global timeseries_label
    data = []
    count = 0
    reading = 0
    timeseries = [] #force to refresh for multiple curve only have one time series.
    timeseries_label = [] #force to refresh for multiple curve only have one time series.
    #print("First record in the mac -----------") + fullset[0]
    #print("\n")*2
    #print("last record in the mac -----------") + fullset[-1]
    for k in fullset:
        item = ast.literal_eval(k)
        #option #1 use the time coming from score
        time = r.zscore(mac, k) 
        #option #2 use the time coming from score
        #time = int(list(item['utctime'])[0], 16)
        # this is a little contradictary, no matter what field it is checking, 
        # as long as the value is empty, replace it with 0
        if (item[typeOfSensor] == ' '):
            #print("hit the null item in deviceUptime, exit")
            #exit()
            reading = 0 
        elif (typeOfSensor == 'temp'):
            reading = ADC_TempConversionSMT(int(item[typeOfSensor], 16))
        elif (typeOfSensor == 'humid'):
            readingTemp = ADC_TempConversionSMT(int(item['temp'], 16))
            reading = calcHumidity(int(item[typeOfSensor], 16), readingTemp)
        elif (typeOfSensor == 'battery'):
            reading = float(item[typeOfSensor])
        elif (typeOfSensor == 'workingMemory'):
            reading = int((item[typeOfSensor]), 16)
        elif (typeOfSensor == 'deviceUptime'):
            reading = int((item[typeOfSensor]), 16)
        else:
            reading = float(item[typeOfSensor])
        #timeseries.append(time)
        timeseries_label.append(item['utctime'])
        data.append([time, reading])
        #print(item['utctime']+ "+"*int(printToScreen(60, 90, reading)))
        #print(item['utctime']+ "-----------" + item[typeOfSensor]+"--------"+str(reading))
        #print(str(data))
        count+=1
    return data

def pick_v2(mac, start, end, typeOfSensor):
    fulllist = r.smembers('allSensors')
    #print(fulllist)
    #print(i)
    #fullset = r.zrange(mac, 0, -1)
    fullset = r.zrangebyscore(mac, 1429000000, "+inf")
    #fullset = r.zrange(mac, 0, -1, 'WITHSCORES') #for some reason, the "withscores" option doesn't work
    #fullset = r.zrangebyscore(mac, start, end)
    print(str(mac)+" ======== Totally "+ str(len(fullset))+ " data points!")
    global timeseries_label
    data = []
    count = 0
    reading = 0
    timeseries = [] #force to refresh for multiple curve only have one time series.
    timeseries_label = [] #force to refresh for multiple curve only have one time series.
    #print("First record in the mac -----------") + fullset[0]
    #print("\n")*2
    #print("last record in the mac -----------") + fullset[-1]
    for k in fullset:
        item = ast.literal_eval(k)
        #option #1 use the time coming from score
        time = r.zscore(mac, k) 
        #option #2 use the time coming from score
        #time = int(list(item['utctime'])[0], 16)
        # this is a little contradictary, no matter what field it is checking, 
        # as long as the value is empty, replace it with 0
        if (item[typeOfSensor] == ' '):
            #print("hit the null item in deviceUptime, exit")
            #exit()
            reading = 0 
        elif (typeOfSensor == 'temp'):
            reading = ADC_TempConversionSMT(int(item[typeOfSensor], 16))
        elif (typeOfSensor == 'humid'):
            readingTemp = ADC_TempConversionSMT(int(item['temp'], 16))
            reading = calcHumidity(int(item[typeOfSensor], 16), readingTemp)
        elif (typeOfSensor == 'battery'):
            reading = float(item[typeOfSensor])
        elif (typeOfSensor == 'workingMemory'):
            reading = int((item[typeOfSensor]), 16)
        elif (typeOfSensor == 'deviceUptime'):
            reading = int((item[typeOfSensor]), 16)
        else:
            reading = float(item[typeOfSensor])
        #timeseries.append(time)
        timeseries_label.append(item['utctime'])
        data.append([time, reading])
        #print(item['utctime']+ "+"*int(printToScreen(60, 90, reading)))
        #print(item['utctime']+ "-----------" + item[typeOfSensor]+"--------"+str(reading))
        #print(str(data))
        count+=1
    return data


class CanvasPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.figure = Figure()
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.canvas.mpl_connect('button_press_event', self.button_press_callback)
        self.canvas.mpl_connect('button_release_event', self.button_release_callback)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.listAll = {}
        self.Fit()
        self.x0 = 0
        self.x1 = 0
        global macList
        global modalities
        self.macs = macList
        self.mod = modalities

    def button_press_callback(self, event):
        if event.button !=1: return
        #print(event.xdata,event.ydata)
        x0 = event.xdata

    def button_release_callback(self, event):
        if event.button !=1: return
        #print(event.xdata,event.ydata)
        x1 = event.xdata
        print(self.macs, self.mod)
        self.drawMulti_v2(self.macs, self.mod)

    def draw(self):
        t = arange(0.0, 3.0, 0.01)
        s = sin(2 * pi * t)
        self.axes.plot(t, s)

    def drawMulti(self, macList, typeOfSensor):
        timeseries = []
        count = 0
        caption = ''
        data = []
        for mac in macList: 
            data = pick(mac, typeOfSensor) 
            self.listAll[mac] = zip(*data)[1]
            timeseries = zip(*data)[0]
            self.axes.plot(timeseries, self.listAll[mac], colorList[count % NUM_OF_COLORS], label=mac)
            self.axes.legend(loc=2)
            count+=1
            #print("Time series is =================> ") + str(timeseries)
            #print("data points is =================> ") + str(self.listAll[mac] )
        if (typeOfSensor == 'temp'):
            self.axes.set_ylim([32, 100])
            caption = "Temperature Reading "
        elif (typeOfSensor == 'humid'):
            self.axes.set_ylim([0, 100])
            caption = "Humidity Reading "
        elif (typeOfSensor == 'battery'):
            self.axes.set_ylim([0, 5.0])
            caption = "Battery Reading "
        elif (typeOfSensor == 'workingMemory'):
            self.axes.set_ylim([0, 4000])
            caption = "Working Memory Usage "
        elif (typeOfSensor == 'rssi'):
            self.axes.set_ylim([-150, 0])
            caption = "Received Signal Strength Index (RSSI) Reading "
        elif (typeOfSensor == 'deviceUptime'):
            self.axes.set_ylim([0, (timeseries[-1]-timeseries[0]+ 1000)])
            caption = "Device Up Time "
        elif (typeOfSensor == 'transid'):
            self.axes.set_ylim([0, 300])
            caption = "TransID over Time "
        elif (typeOfSensor == 'tranid'):
            self.axes.set_ylim([0, 300])
            caption = "Sensor Internal TranID Over Time "
        else:
            self.axes.set_ylim([0, 100])
        self.axes.set_title(caption + " Display")
        self.axes.grid(b=True, which='both', color='r', linestyle='--')
        self.axes.set_xticks( discrete(timeseries, 120))
        self.axes.set_xticklabels( discrete(timeseries_label, 120), rotation = 90, ha='center')

    def drawMulti_v2(self, macList, listOfSensors):
        global setCaptions
        timeseries = []
        count = 0
        caption = ''
        data = []
        range = []
        scaler = 0
        print("sensor list is: "), listOfSensors
        for mac in macList: 
            for typeOfSensor in listOfSensors:
                print("now comes to "), mac, " and ", typeOfSensor
                data = pick(mac, typeOfSensor) 
                self.listAll[mac] = zip(*data)[1]
                #print(self.listAll[mac])
                timeseries = zip(*data)[0]
                range = (sensorDef[typeOfSensor])['range']
                scaler = range[1] - range[0]
                self.axes.plot(timeseries, map(lambda x: abs(x/scaler*100.0), self.listAll[mac]), colorList[count % NUM_OF_COLORS], label=mac+" "+typeOfSensor)
                setCaptions.add((sensorDef[typeOfSensor])['caption'])
                self.axes.legend(loc=2)
                count+=1
                #print("Time series is =================> ") + str(timeseries)
                #print("data points is =================> ") + str(self.listAll[mac] )
 
        self.axes.set_ylim([0, 150])
        self.axes.set_title(', '.join(setCaptions)+" Display")
        self.axes.grid(b=True, which='both', color='r', linestyle='--')
        self.axes.set_xticks( discrete(timeseries, 120))
        self.axes.set_xticklabels( discrete(timeseries_label, 120), rotation = 90, ha='center')

def discrete(listA, freq):
    count = 0
    res = []
    for i in listA:
        if (count % freq) == 0:
            res.append(i)
        count+=1
    #let's also pad on the last reading to the end no matter what it is.
    # for any reason it is not a full round, replace the last tick with
    # existing last data point with the latest one to ensure an update-to-date
    # data display. We don't want to just pad the latest reading be:
    # at some point, the latest reading could be too close to the last round one.
    if ( res[-1] != listA[-1]):
        res[-1] = listA[-1]
    return res

if __name__ == "__main__":
    app = wx.PySimpleApp()
    fr = wx.Frame(None, title='test')
    panel = CanvasPanel(fr)
    global macList
    global modalities
    if (len(sys.argv) < 2):
        print("error command format")
        print("Should be:")
        print(">python wdt_plot_client.py temp")
        exit()
    elif (len(sys.argv) == 2):
        panel.drawMulti([#"00c0b700008280cd", 
                    #"00c0b70000827975",
                    #'00c0b700008c847e',
                    #'00c0b700008279bf',
                    #'00c0b700008281df'
                    '00c0b700008280ae',
                    '00124b00039ac6fb',
                    '00c0b700008279cf',
                    '00c0b700008c845a'
                    ], 
                    sys.argv[1])
    #print(sys.argv[1],sys.argv[2])
    else:
        macList = [#"00c0b700008280cd", 
                    #"00c0b70000827975",
                    #'00c0b700008c847e',
                    #'00c0b700008276c7',
                    #'00c0b70000827971',
                    #'00c0b700008279cf',
                    #'00c0b700008280a3',
                    #'00c0b700008279bf',
                    #'00c0b700008281df'
                    '00c0b700008280ae',
                    '00124b00039ac6fb',
                    '00c0b700008279cf',
                    '00c0b700008c845a'
                    ] 
        modalities = sys.argv[1::]
        panel.drawMulti_v2(macList, modalities)
    fr.Show()
    app.MainLoop()
