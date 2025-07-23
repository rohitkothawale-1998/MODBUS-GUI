import redis
import ast 
import sys
import math
r = redis.StrictRedis(host='localhost', port=6379, db =0)
SCREENSIZE = 80

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
    print(fulllist)
    #print(i)
    fullset = r.zrange(mac, 0, -1)
    print(len(fullset))
    print(str(mac)+" ======== Totally "+ str(len(fullset))+ " data points!")
    for k in fullset:
        item = ast.literal_eval(k)
	temperature = ADC_TempConversionSMT(int(item[typeOfSensor], 16))
        print(item['utctime']+ "+"*int(printToScreen(60, 90, temperature)))
        #print(item['utctime']+ "-----------" + item[typeOfSensor]+"--------"+str(temperature))

if __name__ == "__main__":
    pick(sys.argv[1], sys.argv[2])
