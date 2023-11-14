# ----------------------------------------------------------------------
#
#    Power Monitoring (Basic solution) -- This digital solution measures,
#    reports and records both AC power and current consumed by an electrical 
#    equipment, so that its energy consumption can be understood and 
#    taken action upon. This version comes with one current transformer 
#    clamp of 20A that is buckled up to the electric line the equipment 
#    is connected to. The solution provides a Grafana dashboard that 
#    displays current and power consumption, and an InfluxDB database 
#    to store timestamp, current and power. 
#
#    Copyright (C) 2022  Shoestring and University of Cambridge
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see https://www.gnu.org/licenses/.
#
# ----------------------------------------------------------------------
 

# run at poll rate
# make requests
# extract variables
# output variables

import datetime
import logging
import multiprocessing
import time

import importlib
import zmq
import modbus_sensor as sen
# import calculate as calc

logger = logging.getLogger("main.measure")
context = zmq.Context()


class CurrentMeasureBuildingBlock(multiprocessing.Process):
    def __init__(self, config, zmq_conf):
        super().__init__()

        self.config = config
        self.constants = config['constants']

        # declarations
        self.zmq_conf = zmq_conf
        self.zmq_out = None

        self.collection_interval = config['sampling']['sample_interval']
        self.sample_count = config['sampling']['sample_count']

    def do_connect(self):
        self.zmq_out = context.socket(self.zmq_conf['type'])
        if self.zmq_conf["bind"]:
            self.zmq_out.bind(self.zmq_conf["address"])
        else:
            self.zmq_out.connect(self.zmq_conf["address"])

    def run(self):
        logger.info("started")
        self.do_connect()

        # timezone determination
        __dt = -1 * (time.timezone if (time.localtime().tm_isdst == 0) else time.altzone)
        tz = datetime.timezone(datetime.timedelta(seconds=__dt))
        #
        today = datetime.datetime.now().date()
        next_check = (datetime.datetime(today.year, today.month, today.day) + datetime.timedelta(days=1)).timestamp()

        run = True
        period = self.collection_interval


        adapter_addr = self.config["modbus"]["adapter_addr"]
        adapter_port = self.config["modbus"]["adapter_port"]
        slave_id = self.config["modbus"]["slave_id"]
#        voltage = self.config["modbus"]["fixed_voltage"]
        machine_name = self.config["constants"]["machine"]

        num_samples = 0
        sample_accumulator = 0

        sleep_time = period
        t = time.time()
        
        while run:
            t += period
            sensor = sen.ModbusPower(adapter_addr, adapter_port)
            # Collect samples from ADC
            try:
                reading = sensor.action_push(slave_id, machine_name)
                sample = reading['reading1']
                # sample = sensor
                # logger.info("CurrentMeasureBuildingBlock- STAGE-3 done")
                sample_accumulator += sample
                num_samples+=1
            except Exception as e:
                logger.error(f"Sampling led to exception{e}")

            # handle timestamps and timezones
            if time.time() > next_check:
                __dt = -1 * (time.timezone if (time.localtime().tm_isdst == 0) else time.altzone)
                tz = datetime.timezone(datetime.timedelta(seconds=__dt))
                # set up next check
                today = datetime.datetime.now().date()
                next_check = (datetime.datetime(today.year, today.month, today.day) + datetime.timedelta(
                    days=1)).timestamp()

            # dispatch messages
            if num_samples >= self.sample_count:
                average_sample = sample_accumulator / self.sample_count
                num_samples = 0
                sample_accumulator = 0
                print(average_sample)
                logger.info(f"current_reading: {average_sample}")



                # capture timestamp
                timestamp = datetime.datetime.now(tz=tz).isoformat()

                # convert
                # results = calculation.calculate(average_sample)
                # payload = {**results, **self.constants, "timestamp": timestamp}
                payload = {"machine": self.constants['machine'], "Current_1": str(reading['reading1']), "Voltage_1": str(reading['reading2']), "Current_2": str(reading['reading3']), "Voltage_2": str(reading['reading4']), "Current_3": str(reading['reading5']), "Voltage_3": str(reading['reading6']), "Power_kW": str(reading['reading7']), "Power_kVA": str(reading['reading8']), "Power_kVAR": str(reading['reading9']), "Power_Factor": str(reading['reading10']), "sensor": "Modbus", "timestamp": timestamp}
                # send
                output = {"path": "", "payload": payload}
                self.dispatch(output)

            # handle sample rate
            if sleep_time <= 0:
                logger.warning(f"previous loop took longer that expected by {-sleep_time}s")
                t = t - sleep_time  # prevent free-wheeling to make up the slack

            sleep_time = t - time.time()
            time.sleep(max(0.0, sleep_time))
        logger.info("done")

    def dispatch(self, output):
        logger.info(f"dispatch to { output['path']} of {output['payload']}")
        self.zmq_out.send_json({'path': output.get('path', ""), 'payload': output['payload']})
