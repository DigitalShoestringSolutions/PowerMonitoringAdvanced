
########### PACKAGES ####
# pymodbus==2.5.3
# pyserial==3.5
# six==1.16.0

# @decoded by ANAND on Jun 2023
#########################

# configuration of address in datasheet pg 48 here:
# https://docs.rs-online.com/02cb/0900766b814cca5d.pdf

from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.transaction import ModbusRtuFramer as ModbusFramer
import time
from datetime import datetime
import os
import tomli
import logging
import logging.handlers



logger = logging.getLogger('main.measure.sensor')


########### HOBUT MFM 850 LTHN  Register Map####
# 0x0006 = v1
# 0x0008 = v2
# 0x000A = v3
# 0x000C = I1
# 0x000E = I2
# 0x0010 = I3
# 0x0012 = kW sum
# 0x001E = Hz
#########################
current1 = 0x000C
voltage1 = 0x0006
current2 = 0x000E
voltage2 = 0x0008
current3 = 0x0010
voltage3 = 0x000A
kW_reg = 0x0012
kVA_reg = 0x0014
kVAR_reg = 0x0016
f_reg = 0x001E
pf_reg = 0x0018


class ModbusPower:

    def __init__(self, adapter_addr, adapter_port=502):
        self.client = ModbusTcpClient(adapter_addr, port=adapter_port, framer=ModbusFramer)

    def register_read(self, addr, count, slave):
        res = self.client.read_input_registers(address=addr, count=int(count), unit=int(slave))
        decoder = BinaryPayloadDecoder.fromRegisters(res.registers, Endian.Big, wordorder=Endian.Little)
        reading = decoder.decode_32bit_float()
        return reading

    def action_push(self, slave_id, machine_name):
        readings = {}

        readings['reading1'] = self.register_read(current1, 4, slave_id)
        time.sleep(0.5)

        readings['reading2'] = self.register_read(voltage1, 4, slave_id)
        time.sleep(0.5)
        
        readings['reading3'] = self.register_read(current2, 4, slave_id)
        time.sleep(0.5)

        readings['reading4'] = self.register_read(voltage2, 4, slave_id)
        time.sleep(0.5)
        
        readings['reading5'] = self.register_read(current3, 4, slave_id)
        time.sleep(0.5)

        readings['reading6'] = self.register_read(voltage3, 4, slave_id)
        time.sleep(0.5)
        
        readings['reading7'] = self.register_read(kW_reg, 4, slave_id)
        time.sleep(0.5)
        
        readings['reading8'] = self.register_read(kVA_reg, 4, slave_id)
        time.sleep(0.5)
        
        readings['reading9'] = self.register_read(kVAR_reg, 4, slave_id)
        time.sleep(0.5)
        
        readings['reading10'] = self.register_read(pf_reg, 4, slave_id)
        time.sleep(0.5)
        

        readings['devStat'] = 2



        return readings


