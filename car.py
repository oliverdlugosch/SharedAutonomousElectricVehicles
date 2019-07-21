import time, haversine, trip, datetime, requests, json, csv, copy

class car(object):
    def __init__(self, vin = None, position_lat = None, position_lon = None, \
                 mode = None, ip_address = None, battery_status = None, \
                 battery_capacity = None):
        self.vin = vin
        self.ip_address = ip_address
        self.position = {'lat': position_lat, 'lon': position_lon}
        # Allowed modes are:
            # active - car is currently driving a passsenger from pickup to destination
            # locked - car is currently going to pickup location to pick up customer
            # idle - car is currently idle and waiting for request
            # relocating - car is moving to a different comb
            # charging - car is currently charging
            # en_route_to_charge - car is on its way to a charging station
        self.mode = mode
        self.pickup_location = dict()
        self.time_to_pickup = datetime.timedelta(seconds=0)
        self.destination = dict()
        self.last_relocation_position = {'lat': None, 'lon': None}
        self.rental_time = 0.0
        # We initiate every car as fully charged in the beginning and with a capacity
        # of 50 kWh. Fuel consumption is 15kWh/100km
        self.battery_status = 100.0 # in percent
        self.battery_capacity = 50.0 # in kWh
        self.fuel_consumption = 0.150 # in kWh/km 
        self.count_requests_accepted = 0
        self.count_times = dict()
        self.count_times['active'] = 0
        self.count_times['locked'] = 0
        self.count_times['idle'] = 0
        self.count_times['relocating'] = 0
        self.count_times['charging'] = 0
        self.count_times['ertc'] = 0
        self.count_seconds = dict()
        self.count_seconds['active'] = 0.0
        self.count_seconds['locked'] = 0.0
        self.count_seconds['idle'] = 0.0
        self.count_seconds['relocating'] = 0.0
        self.count_seconds['charging'] = 0.0
        self.count_seconds['ertc'] = 0.0
        self.last_count_seconds_idle = 0.0
        self.last_count_seconds_relocating = 0.0
        self.count_km = dict()
        self.count_km['active'] = 0.0
        self.count_km['locked'] = 0.0
        self.count_km['relocating'] = 0.0
        self.count_km['ertc'] = 0.0
        self.task_list = list()
        self.dispatch_me = {'Flag':False, 'Seconds Left': 0.0}
        self.old_request = None
        self.old_init_day = True
        self.mylasttrip = { 'VIN': None, 'Request-Start-Time': None, 'Request-Start-Lat': None, \
                            'Request-Start-Lon': None, 'Waiting Time': None, \
                            'Request-End-Time': None, 'Request-End-Lat': None, \
                            'Request-End-Lon': None, 'Relocation-Lat': None,\
                            'Relocation-Lon': None, 'Relocation Time': None,\
                            'Idle Time after Request': None, 'Initiation Day?': None}
        self.occupiedCP = None

    def take_trip(self, request, time_gap, init_day_flag, writerIA):
        self.old_request = request
        self.last_count_seconds_relocating = self.count_seconds['relocating']
        self.last_count_seconds_idle = self.count_seconds['idle']
        self.old_init_day = init_day_flag
        self.mode = 'locked'
        self.pickup_location = request.start
        self.rental_time = request.rental_time
        self.time_to_pickup = datetime.timedelta(seconds=self.get_time_to_pickup(self.position, self.pickup_location))
        distance_to_pickup = self.get_routing_distance(self.position, self.pickup_location)/1000.0
        distance_to_dropoff = self.get_routing_distance(self.pickup_location, request.end)/1000.0
        battery_pre_locked_temp = self.battery_status
        battery_pre_active_temp = self.battery_status - \
                                  (distance_to_pickup * self.fuel_consumption * 100.0/self.battery_capacity)
        self.battery_status -= ((distance_to_pickup + distance_to_dropoff)\
                                *self.fuel_consumption*100.0/self.battery_capacity)
        if init_day_flag == False:
            self.count_requests_accepted += 1
        self.task_list.append({'mode': 'locked', \
                               'duration': self.time_to_pickup, \
                               'start time': request.time_start, \
                               'end time': request.time_start + self.time_to_pickup})
        self.task_list.append({'mode': 'active', \
                               'duration': self.time_to_pickup + self.rental_time, \
                               'start time': request.time_start + self.time_to_pickup,\
                               'end time': request.time_start + self.time_to_pickup + self.rental_time})
        if init_day_flag == False:
            self.count_seconds['idle'] += time_gap.seconds
            self.count_seconds['locked'] += self.task_list[-2]['duration'].seconds
            self.count_seconds['active'] += self.task_list[-1]['duration'].seconds
            self.count_times['locked'] += 1
            self.count_times['active'] += 1
            self.count_km['locked'] += distance_to_pickup
            self.count_km['active'] += distance_to_dropoff
        # Writing this request to results
        lineforwriter = (self.vin, \
                         'locked', \
                         self.task_list[-2]['start time'], \
                         self.task_list[-2]['end time'], \
                         self.position['lat'], \
                         self.position['lon'], \
                         self.pickup_location['lat'], \
                         self.pickup_location['lon'], \
                         battery_pre_locked_temp, \
                         init_day_flag)
        writerIA.writerow(lineforwriter)
        lineforwriter = (self.vin, \
                         'active', \
                         self.task_list[-1]['start time'], \
                         self.task_list[-1]['end time'], \
                         self.pickup_location['lat'], \
                         self.pickup_location['lon'], \
                         request.end['lat'], \
                         request.end['lon'], \
                         battery_pre_active_temp, \
                         init_day_flag)
        writerIA.writerow(lineforwriter)
        self.destination = request.end
        self.position = request.end
        return 0

    def get_time_to_pickup(self, point1, point2):
        url = 'http://' + self.ip_address + ':5000/route/v1/driving/' + \
              str(point1['lon']) + ',' + str(point1['lat']) + ';' \
              + str(point2['lon']) + ',' + str(point2['lat']) + '?steps=false'
        counter = 0
        while True:
            try:
                response = requests.get(url)
                readable = response.json()
                return readable['routes'][0]['duration']
                break
            except:
                counter += 1
                print('Trying again - duration')
                if counter == 10:
                    return 120.0*60.0

    def get_routing_distance(self, point1, point2):
        url = 'http://' + self.ip_address + ':5000/route/v1/driving/' + \
              str(point1['lon']) + ',' + str(point1['lat']) + ';' \
              + str(point2['lon']) + ',' + str(point2['lat']) + '?steps=false'
        counter = 0
        while True:
            try:
                response = requests.get(url)
                readable = response.json()
                return readable['routes'][0]['distance']
                break
            except:
                counter += 1
                print('Trying again - distance')
                if counter == 10:
                    return 20000

    def charge(self, targetCP, init_day_flag, current_time, writerIA):
		# Car is being charged
        self.occupiedCP = targetCP
        print("Car ", self.vin, " will be charged at CP ", self.occupiedCP['UIN'], " which is ", \
              self.occupiedCP['Occupied'], ". Its current position is ", self.position, \
              " and its CP would be at ", targetCP['lat'], targetCP['lon'], ". Its battery is ", \
              self.battery_status)
        self.mode = 'ertc'
        #This is a temporary variable
        target = dict()
        target['lat'] = targetCP['lat']
        target['lon'] = targetCP['lon']
        distance_to_CP = self.get_routing_distance(self.position, target)/1000.0
        ERTC_duration = datetime.timedelta(seconds=self.get_time_to_pickup(self.position, target))
        print("The ERTC Duration for car ", self.vin, "  is ", ERTC_duration.total_seconds())
        battery_pre_ertc_temp = self.battery_status
        self.battery_status -= ((distance_to_CP * self.fuel_consumption)*100.0 / self.battery_capacity)
        battery_pre_charging_temp = self.battery_status
        charging_duration = datetime.timedelta(hours=((100.0 - self.battery_status)*self.battery_capacity)/(100.0*targetCP['Power']))
        print("The Charging Duration for car ", self.vin, " is ", charging_duration.total_seconds())
        self.battery_status = 100.0
        if init_day_flag == False:
            self.count_times['ertc'] += 1
            self.count_times['charging'] += 1
        self.task_list.append({'mode': 'ertc', \
                               'duration': ERTC_duration, \
                               'start time': current_time, \
                               'end time': current_time + ERTC_duration})
        self.task_list.append({'mode': 'charging', \
                               'duration': charging_duration, \
                               'start time': current_time + ERTC_duration,\
                               'end time': current_time + ERTC_duration + charging_duration})
        if init_day_flag == False:
            self.count_seconds['ertc'] += self.task_list[-2]['duration'].seconds
            self.count_seconds['charging'] += self.task_list[-1]['duration'].seconds
            self.count_km['ertc'] += distance_to_CP
            # Writing out this request
        lineforwriter = (self.vin, \
                         'ertc', \
                         self.task_list[-2]['start time'], \
                         self.task_list[-2]['end time'], \
                         self.position['lat'], \
                         self.position['lon'], \
                         targetCP['lat'], \
                         targetCP['lon'], \
                         battery_pre_ertc_temp, \
                         init_day_flag)
        writerIA.writerow(lineforwriter)
        lineforwriter = (self.vin, \
                         'charging', \
                         self.task_list[-1]['start time'], \
                         self.task_list[-1]['end time'], \
                         targetCP['lat'], \
                         targetCP['lon'], \
                         targetCP['lat'], \
                         targetCP['lon'], \
                         battery_pre_charging_temp, \
                         init_day_flag)
        writerIA.writerow(lineforwriter)
        self.destination['lat'] = targetCP['lat']
        self.destination['lon'] = targetCP['lon']
        self.position = self.destination
        return 0

    def relocate(self, target_comb, current_time, destination, init_day_flag, writerIA):
        self.mode = 'relocating'
        self.destination = destination
        time_to_get_there = datetime.timedelta(seconds=self.get_time_to_pickup(self.position, destination))
        distance_to_relocation = self.get_routing_distance(self.position, self.destination)/1000.0
        battery_pre_relocating_temp = self.battery_status
        self.battery_status -= ((distance_to_relocation * self.fuel_consumption)*100.0 / self.battery_capacity)
        if init_day_flag == False:
            self.count_times['relocating'] += 1
            self.count_seconds['relocating'] += time_to_get_there.seconds
            self.count_km['relocating'] += distance_to_relocation
        self.task_list.append({'mode': 'relocating', \
                               'duration': time_to_get_there, \
                               'start time': current_time, \
                               'end time': current_time + time_to_get_there})
        lineforwriter = (self.vin, \
                         'relocating', \
                         self.task_list[-1]['start time'], \
                         self.task_list[-1]['end time'], \
                         self.position['lat'], \
                         self.position['lon'], \
                         self.destination['lat'], \
                         self.destination['lon'], \
                         battery_pre_relocating_temp, \
                         init_day_flag)
        writerIA.writerow(lineforwriter)
        self.position = destination
        self.last_relocation_position = destination
        target_comb.car_sign_in(self)
        return 0
