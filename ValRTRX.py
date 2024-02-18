#!/usr/bin/python3
import sys
import time
import argparse
import serial.rs485
#pip3 install --user libscrc
import libscrc
#pip3 install --user paho-mqtt
#import paho.mqtt.client as mqtt



debug=False #set to true to enable debugging
sPort = '/dev/ttyUSB0'

req_init = "000300fc0000842b"

req_ids_loop = ["ff4306064246", "ff4306064246", "ff5006003381",
                "ff500601f241", "ff500602b240", "ff5006037380", "ff5006043242", "ff500605f382"]

req_data = bytes.fromhex("030029001b")

req_bat_active = bytes.fromhex("ff4112")

current_bat_id = 2
bat_ids = []
bat_dupes = []
additional_reqs = []


def sHEX(hexstr):
    if hexstr > 32767:
        hexstr = hexstr - 65536
    return hexstr


parser=argparse.ArgumentParser()
parser.add_argument('-d',action="store_true",help="enable debugging")
parser.add_argument('-port',help="serial port (default /dev/ttyUSB0)",default="/dev/ttyUSB0")
parser.add_argument('-baud',help="serial baud rate (default 115200",default=115200)


args=parser.parse_args()
debug=args.d
sPort=args.port
baud=args.baud

s = serial.Serial(
    port=sPort,
    baudrate=baud,
    # parity=serial.PARITY_MARK,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0.005
)

#s.rs485_mode = serial.rs485.RS485Settings(True, False, False, None, None)

s.write(bytes.fromhex(req_init))
time.sleep(0.001)
s.write(bytes.fromhex(req_init))
time.sleep(0.001)


def evaluate_battery_status(batteryNum,batHexID):
    soc = cc[43] / 255 * 100
    current1 = sHEX((cc[24] * 256) + cc[23]) / 1000
    current2 = sHEX((cc[28] * 256) + cc[27]) / 1000
    voltage_bat = sHEX((cc[36] * 256) + cc[35]) / 1000
    p_bat = voltage_bat * current1
    voltage_1 = sHEX((cc[50] * 256) + cc[49]) / 1000
    voltage_2 = sHEX((cc[52] * 256) + cc[51]) / 1000
    voltage_3 = sHEX((cc[54] * 256) + cc[53]) / 1000
    voltage_4 = sHEX((cc[56] * 256) + cc[55]) / 1000
    voltage_5 = sHEX((cc[32] * 256) + cc[31]) / 1000  # same as v4
    voltage_6 = sHEX((cc[34] * 256) + cc[33]) / 1000  # same as v1
    charge_cycle = sHEX((cc[14] * 256) + cc[13])  # maybe it is
    t1 = cc[3]
    t2 = cc[5]
    t3 = cc[17]
    t4 = cc[18]
    t5 = cc[4]
    t6 = cc[6]
    print("BatteryNumber: ", batteryNum)
    print("BatteryHexID: ", batHexID)
    #print("SOC: ", str(soc), "%")
    print("Bat%02d_SOC:%s%%" %  (batteryNum, str(soc)) )
    #client.publish(args.topicprefix + key, value)
    print("I1: ", str(current1), "A")
    print("Ubat: ", str(voltage_bat), "V")
    print("P: ", str(p_bat), "W")
    print("U1: ", str(voltage_1), "V")
    print("U2: ", str(voltage_2), "V")
    print("U3: ", str(voltage_3), "V")
    print("U4: ", str(voltage_4), "V")
    if (debug==1):
        print("U5: ", str(voltage_5), "V")  # very close to U5
        print("U6: ", str(voltage_6), "V")  # very close to U1
    print("T1: ", str(t1), "C")
    print("T2: ", str(t2), "C")
    print("T3 (PCB): ", str(t3), "C")
    print("T4 (PCB): ", str(t4), "C")
    print("T5: ", str(t5), "C")
    print("T6: ", str(t6), "C")
    if (debug==1):
        print(" I2: ", str(current2), "A (sometimes much (20-33%) lower then I1 and measured charging current. why? maybe reduced by the loss of the balancer? seems to happen with higher charging currents, same with 2A, and with I1 -4.969 I2 was -3.399A)")
    print(" Charge cycles?: ", str(charge_cycle), "maybe, could be something else")


for i in range(0, 2): 
    for req in req_ids_loop:
        if (debug==1):
            print("->", req)
        s.write(bytes.fromhex(req))
        time.sleep(0.03)
        cc = s.readline()
        if len(cc) > 0:
            if (debug==1):
              print("<-", cc.hex())
            if cc.hex().startswith("ff70"):
                # received id from battery
                bat_id = cc[3:15]
                bat_id_hex = bat_id.hex()
                if bat_id_hex in bat_dupes:  # skip duplicates
                    print("skipping duplicate id ", bat_id_hex)
                    continue
                bat_dupes.append(bat_id_hex)

                req = req_bat_active + bat_id + bytes([current_bat_id])
                bat_ids.append(current_bat_id)
                current_bat_id += 1
                req = req + libscrc.modbus(req).to_bytes(2, 'little')
                
                if (debug==1):
                    print("-> ", req.hex(), "# received battery id", bat_id_hex,
                      "assigning bus id", current_bat_id - 1)
                s.write(req)
                time.sleep(0.035)
                print(s.readline().hex(), "# response of set active bat id")

            if len(cc) >= 58 and cc.hex().startswith("0203"):
                print ("Debug: I dont run")
                evaluate_battery_status()


batteryCount=0
for reqid in bat_ids:
    batteryCount=batteryCount+1 #TODO use reqid
    req = bytes([reqid]) + req_data
    req = req + libscrc.modbus(req).to_bytes(2, 'little')
    if (debug==1):
        print("->", req.hex(), "# request data from bus id", reqid)
    s.write(req)
    time.sleep(0.03)
    cc = s.readline()
    for i in range(0, 2):
        cc += s.readline()

    if (debug==1):
        print("<-", cc.hex(), "# battery data")
    if len(cc) >= 58:
        evaluate_battery_status(batteryCount,bat_dupes[batteryCount-1])

s.close()
