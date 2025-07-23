import time
import redis
import ast
RedisServer = '10.169.104.184'
r = redis.StrictRedis(host=RedisServer, port=6379, db =0)
r.hmset("myhash", {"field1":"aa", "field2":"bb"})
dict = r.hgetall("myhash")
for k in dict:
    print(k, dict[k] )

#sdp = {'mac':'00c0b700008c0000', 'MFGData':'06052014'}
mac = '00c0b700008280a3'
listOfSensors = r.smembers('allSensors')
print(listOfSensors)
#r.zadd(mac, 55399343, sdp)
list = r.zrange(mac, 0, -1 )
#print(score)
#print(list)
listS = [] 
allMarks = {}
start = 0
end = 0
for mac in listOfSensors:
    listS = []
    list = r.zrevrange(mac, 0, 20)
    start = time.time()
    for k in list:
        #score = r.zscore(mac, k)
	item = ast.literal_eval(k)
        #score = item['utctime']
	if (mac == 'PowerMeter'):
	#if (mac == '00c0b70000827a05'):
            print(" item :") + str(item)
        score = item
        listS.append(score)
    allMarks.update({mac:listS})
    end  = time.time()
    print(str(len(listS))+"records, it takes "+str(end - start)+ " seconds for MAC: "+str(mac))
#print(allMarks)
