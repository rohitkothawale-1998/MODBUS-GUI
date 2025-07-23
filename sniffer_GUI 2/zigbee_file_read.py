import struct
record_format = '<10sHHI34sI8s'
input = open("C4f4-1101-00010050-NBPD0180APP.zigbee",'rb')
def readall():
    while 1:
        record = input.read(struct.calcsize(record_format))
        if record == '':
            input.close()
            break
        result_list=struct.unpack(record_format, record)
        print(result_list)

def pick(offset, size, f):
    input.read(offset)
    record = input.read(size)
    return record

result_list= []
result_list= struct.unpack(record_format, pick(0,64,input)) 

print(struct.unpack(record_format, pick(2*65536, 64, input)))
print("MFG ID is:"), hex(result_list[1])
print("pkgtype is:"), hex(result_list[2])
print("pkg version is:"), hex(result_list[3])
print("File size is:"), result_list[5]

