import car, database, trip, datetime, csv, scipy, numpy, comb, haversine, math, requests, json
import matplotlib.path as mpltPath
from random import shuffle

class model(object):
    def __init__(self, location, number_of_cars, number_of_CPs, firstday, lastday, training_percentage, timestep, EIT_radius, comb_diameter, ip_address, minimum_cars, maximum_cars):
        # Base data is stored/allocated
        self.location = location
        self.number_of_cars = number_of_cars
        self.number_of_CPs = number_of_CPs
        self.firstday = firstday
        self.lastday = lastday
        self.ip_address = ip_address
        self.cars = list()
        self.cars = self.initiate_cars(number_of_cars)
        self.training_percentage = training_percentage
        self.i_time = 0

        # Trip data is initiated
        self.trips = list()
        self.trips = self.load_trips()
        self.EIT_trips = None
        self.requests = None
        self.EIT_map = dict()
        self.current_time = None
        self.final_time = None
        self.timestep = timestep
        self.tracker_requests = 0

        # Geographical data - maximum and minimum longitude and latitude in rental data
        self.lat_max = 0.0
        self.lat_min = 0.0
        self.lon_max = 0.0
        self.lon_min = 0.0

        # EIT and comb data
        self.combs = list()
        self.lon_delta = 0.0
        self.lat_delta = 0.0
        self.EIT_radius = EIT_radius / 1000.0
        self.comb_diameter = comb_diameter / 1000.0
        self.timewindow_EIT = datetime.timedelta(minutes=60.0)
        self.minimum_cars = minimum_cars
        self.maximum_cars = maximum_cars

        # Charging Points
		# If new CP shuffle needs to be done, uncomment next line and comment out the following
        # If CPs should be loaded, vice versa, and look at section marked "PART 2"
		# self.CPs = self.load_CPs_json(location) # loads Charge Points based on json file
		self.load_CPs_csv(self.number_of_CPs) # simply loads Charge Points from csv list
        
    def run(self):
        trip_number = 0
        # Preparing trips and requests and running simulation
        self.writetrips(r'./_init/trips_raw.csv')
        # Uncleaned set of trips has been written to output.
        # Clean trip data, sort by start time and write data to output.
        print('Trips have been loaded. Cleaning trips ...')
        self.cleantrips()
        self.trips = sorted(self.trips, key=lambda trip: trip.time_start)
        self.writetrips(r'./_init/trips_cleaned.csv')
        print('Trips have been cleaned.')
        # Trips are separated into EIT_trips and requests.
        self.EIT_trips = self.pick_EIT_trips()
        self.requests = self.pick_requests()
        # Comb grid is being created.
        self.find_extremes()
        self.calculate_lon_lat_delta()
        self.create_grid()
        print('Grid has been created.')
        self.deactivate_unused_combs()
        print('Unused combs have been deactivated.')
        self.calculate_EIT_map()
        print('EITs have been calculated.')
        self.write_EIT_map(r'./_init/EIT_map.csv')

        # PART 2
		# Cleans, shuffles, and writes entire CP list - uncomment following line
        # self.CP_module()
        # Loads given number of CPs to self.CPs - uncomment following line
        # self.load_CPs_csv(self.number_of_CPs)

        wrIAfile = open(r'./_results/Individual Action.csv', 'w')
        writerIA = csv.writer(wrIAfile, delimiter=";", lineterminator='\n')
        header1 = ('VIN', 'Type', 'Start Time', 'End Time',\
                   'Start Lat', 'Start Lon', \
                   'End Lat', 'End Lon', \
                   'Battery at Start', 'Initiation Day?')
        writerIA.writerow(header1)
        default_request = self.requests[0]
        # Cars are positioned randomly within active combs
        self.position_cars(default_request)
        self.current_time = self.EIT_trips[-1].time_start
        self.final_time = self.requests[-1].time_end + datetime.timedelta(hours=1)
        self.i_time = 0
        init_day_flag = True
        while self.current_time <= self.final_time:
            # Do not store information on/do not evaluate initiation day
            if self.current_time > self.EIT_trips[-1].time_start + datetime.timedelta(days=1):
                init_day_flag = False
            if self.i_time % 600 == 0:
                print('The current time is: ', self.current_time)
                print('The current trip number is: ', trip_number)
                n_now = 0
                for car in self.cars:
                    if car.mode == 'idle':
                        n_now += 1
                print('There are ', n_now ,' idle cars right now.')
                n_now = 0
                for car in self.cars:
                    if car.mode == 'relocating':
                        n_now += 1
                print('There are ', n_now ,' relocating cars right now.')
                n_now = 0
                for car in self.cars:
                    if car.mode == 'charging':
                        n_now += 1
                print('There are ', n_now ,' charging cars right now.')
                n_now = 0
                for car in self.cars:
                    if car.mode == 'active':
                        n_now += 1
                print('There are ', n_now ,' active cars right now.')
                n_now = 0
                for car in self.cars:
                    if car.mode == 'locked':
                        n_now += 1
                print('There are ', n_now ,' locked cars right now.')
                n_now = 0
                for car in self.cars:
                    if car.mode == 'ertc':
                        n_now += 1
                print('There are ', n_now ,' ertc cars right now.')
            current_requests = self.find_current_requests()
            trip_number = trip_number + len(current_requests)
            if len(current_requests) != 0:
                self.request_module(current_requests, init_day_flag, writerIA)
            self.task_module(init_day_flag, writerIA)
            self.update_module(init_day_flag)
            self.current_time = self.current_time + datetime.timedelta(seconds=self.timestep)
            self.i_time += 1
            wrIAfile.flush()
        wrIAfile.close()
        return 0

    def load_CPs_json(self, location):
        CPs = list()
        temp = r'./_init/%s.json' % location
        with open(temp) as json_data:
            response = json.load(json_data)
        UIN = 0
        for item in response:
            UIN += 1
            CPs.append({'UIN':UIN, 'lat':item['AddressInfo']['Latitude'],
                        'lon':item['AddressInfo']['Longitude'], 'Occupied':False,
                        'Power':11.0})
        print(len(response), " Charging Points found and loaded.")
        return CPs

    def find_me_a_destination(self, comb):
        flag = True
        result = dict()
        while flag:
            result['lat'] = (comb.P3['lat'] - comb.P5['lat']) * \
                                  numpy.random.random() + comb.P5['lat']
            result['lon'] = (comb.P1['lon'] - comb.P4['lon']) * \
                                  numpy.random.random() + comb.P4['lon']
            if self.point_in_comb(comb, result) == True:
                flag = False
        return result

    def initiate_cars(self, number_of_cars):
        # Initiates cars - gives VIN
        result = list()
        for i in range(number_of_cars):
            result.append(car.car(i,0.0,0.0,'idle',self.ip_address))
        return result

    def load_trips(self):
        # Loading all trips.
        # Identify all relevant vehicles through their \
        # Vehicle Identification Number (VIN).

        db = database
        query = "SELECT DISTINCT vin FROM '%s' WHERE location = \
        '%s' AND timestamp >= '%s' AND timestamp <= '%s'" \
        % (self.location, self.location, self.firstday, self.lastday)
        vins = db.selectDataObjects(query, self.location)
        print('Found ', len(vins), ' vehicles in data source. Loading trip points...')
        return self._getTrips(vins)

    def pick_EIT_trips(self):
        result = self.trips[0:(int)((self.training_percentage/100.0)*len(self.trips))]
        return result

    def pick_requests(self):
        result = self.trips[(int)((self.training_percentage / 100.0) * \
                                  len(self.trips))+1:len(self.trips)]
        return result

    def _getTrips(self, vins):
        trips = list()
        i1 = 0
        for vin in vins:
            if i1 % 50 == 0:
                print(i1, ' of ', len(vins))
            i1 += 1
            tripPoints = self._getTripPoints(vin)
            # There must be at least 2 trip points for one complete trip
            if len(tripPoints) > 1:
                start = {'lat': tripPoints[0][0], 'lon': tripPoints[0][1]}
                start['lat'] = float(start['lat'])
                start['lon'] = float(start['lon'])
                time_start = tripPoints[0][2]
                i3 = 0
                for point in tripPoints[1:]:
                    i3 += 1
                    end = {'lat': point[0], 'lon': point[1]}
                    end['lat'] = float(end['lat'])
                    end['lon'] = float(end['lon'])
                    idle = datetime.datetime.strptime(point[3], "%Y-%m-%d %H:%M:%S.%f") - datetime.datetime.strptime(point[2], "%Y-%m-%d %H:%M:%S.%f")
                    # check if trip already exists
                    if (self.trips == list()) or (any(trip.time_start == time_start and trip.time_end == point[2] \
                       for trip in self.trips) == False):
                        t = trip.trip(start, end, time_start, point[2], idle, vin)
                        trips.append(t)
                    start = end
                    time_start = point[3]
        return trips

    def _getTripPoints(self,vin):
        query = "SELECT lat, lon, timestamp as datetime, timestamp_end as datetime FROM %s WHERE vin = '%s' AND timestamp_end IS NOT '' ORDER BY timestamp"% (self.location, vin[0])
        trip_points = database.selectDataObjects(query, self.location)
        return trip_points

    def writetrips(self, path):
        wr1file = open(path, 'w')
        writer1 = csv.writer(wr1file, delimiter=";", lineterminator='\n')
        header1 = ('StartTime', 'Start-lat', 'Start-lon', 'EndTime', 'End-lat', 'End-lon', 'Duration in minutes', 'IdleTime', 'RentalTime', 'Vin')
        writer1.writerow(header1)
        for t in self.trips:
            header1 = (t.time_start, t.start['lat'], t.start['lon'], \
                       t.time_end, t.end['lat'], t.end['lon'], t.duration.total_seconds()/60.0, t.idle_time, \
                       t.rental_time, t.vin)
            writer1.writerow(header1)
            wr1file.flush()
        wr1file.close()
        return 0

    def cleantrips(self):
        # Take out trips that are out of date, that have negative idle
        # or rental time or that have rental time > 1 day
        itemp = 0
        for t in self.trips:
            if t.time_start.date() < self.firstday or \
            t.time_end.date() > self.lastday or \
            t.rental_time < datetime.timedelta(seconds=0) or \
            t.rental_time > datetime.timedelta(days=1) or \
            t.idle_time < datetime.timedelta(seconds=0):
                t.start = 'POP'
                itemp += 1
        self.trips = [t for t in self.trips if t.start != 'POP']
        print('Found ', itemp, ' bad trips.')
        return 0

    def position_cars(self, default_request):
        # Random between geographical extremes, but only in active combs
        for car in self.cars:
            car.old_request = default_request
            exit_flag = True
            while exit_flag == True:
                car.position['lat'] = (self.lat_max - self.lat_min) * \
                                      numpy.random.random() + self.lat_min
                car.position['lon'] = (self.lon_max - self.lon_min) * \
                                   numpy.random.random() + self.lon_min
                temp_comb = self.find_comb({'lat':car.position['lat'], 'lon':car.position['lon']})
                if temp_comb.active == True:
                    my_comb = self.find_comb(car.position)
                    my_comb.car_sign_in(car)
                    exit_flag = False
        print('Cars have been positioned.')
        return 0

    def find_current_requests(self):
        result = list()
        while self.tracker_requests < len(self.requests) - 1 and\
              self.requests[self.tracker_requests].time_start >= self.current_time and \
              self.requests[self.tracker_requests].time_start < self.current_time + datetime.timedelta(seconds=self.timestep):
            result.append(self.requests[self.tracker_requests])
            self.tracker_requests += 1
        return result

    def find_extremes(self):
        self.lat_min = self.trips[0].start['lat']
        self.lat_max = self.trips[0].start['lat']
        self.lon_min = self.trips[0].start['lon']
        self.lon_max = self.trips[0].start['lon']
        for trip in self.trips:
            if trip.start['lat'] > self.lat_max:
                self.lat_max = trip.start['lat']
            if trip.end['lat'] > self.lat_max:
                self.lat_max = trip.end['lat']
            if trip.start['lat'] < self.lat_min:
                self.lat_min = trip.start['lat']
            if trip.end['lat'] < self.lat_min:
                self.lat_min = trip.end['lat']
            if trip.start['lon'] > self.lon_max:
                self.lon_max = trip.start['lon']
            if trip.end['lon'] > self.lon_max:
                self.lon_max = trip.end['lon']
            if trip.start['lon'] < self.lon_min:
                self.lon_min = trip.start['lon']
            if trip.end['lon'] < self.lon_min:
                self.lon_min = trip.end['lon']
        return 0

    def request_module(self, current_requests, init_day_flag, writerIA):
        # Determine the number of idle cars
        idle_cars = list()
        for car in self.cars:
            # 25% of battery capacity is defined as cutoff 
            if car.mode == 'idle' and car.battery_status >= 25.0:
                idle_cars.append(car)
        if len(idle_cars) < len(current_requests):
            print(' ++++++++++++++++++++++++++++++++++++++++++++++++++++')
            print(' +++ Too few idle cars. Cannot meet all requests. +++')
            print(' ++++++++++++++++++++++++++++++++++++++++++++++++++++')
            if init_day_flag == False:
                self.write_missed_request(init_day_flag, writerIA, current_requests)
            return 0
        for i_request in current_requests:
            # Find closest car for current request
            itemp = 0
            min_dist = self.get_distance(idle_cars[itemp].position, i_request.start)
            min_i = itemp
            time_gap = (i_request.time_start - self.current_time)
            for car in idle_cars:
                if self.get_distance(idle_cars[itemp].position, i_request.start) < \
                    min_dist:
                    min_dist = self.get_distance(idle_cars[itemp].position, i_request.start)
                    min_i = itemp
                itemp += 1
            idle_cars[min_i].take_trip(i_request, time_gap, init_day_flag, writerIA)
            temp_comb = self.find_comb(idle_cars[min_i].position)
            temp_comb.car_sign_out(idle_cars[min_i])
            idle_cars.pop(min_i)
        return 0

    def task_module(self, init_day_flag, writerIA):
        if self.i_time%300 == 150:
            for car in self.cars:
                if car.mode == 'idle':
                    # If battery is lower than 50%, find closest available CP and go there for full charging
                    if car.battery_status < 50.0:
                        itemp = 0
                        #Set the min_distance to 100 km
                        min_dist = 100
                        min_i = None
                        for CP in self.CPs:
                            if CP['Occupied'] == False:
                                if self.get_distance(car.position,{'lat':CP['lat'],'lon':CP['lon']}) < min_dist:
                                    min_dist = self.get_distance(car.position,{'lat':CP['lat'],'lon':CP['lon']})
                                    min_i = itemp
                            itemp += 1
                        if min_i is not None:
                            targetCP = self.CPs[min_i]
                            targetCP['Occupied'] = True
                            car.charge(targetCP, init_day_flag, self.current_time, writerIA)
                        else:
                            print("WE HAVE A PROBLEM WITH CHARGING. PROBABLY ALL CHARGING POINTS FULL.")

                    else: # Battery status >= 50%
                        # First, check if all combs have the minimum number of idle cars
                        results = list()
                        get_out = False
                        for i in range(0, self.minimum_cars):
                        # i goes 0, 1, 2 if self.minimum_cars = 3
                            for comb in self.combs:
                                # check for all ACTIVE combs if minimum number is idle. If not, send car to closest
                                if len(comb.car_list) == i and comb.active == True:
                                    results.append(comb)
                                    get_out = True
                            if get_out == True:
                                break
                        if len(results) != 0:
                            # There apparently is at least one comb with insufficient cars
                            min_dist = self.get_distance(car.position, results[0].center)
                            best_comb = results[0]
                            for comb in results:
                                temp_dist = self.get_distance(car.position, comb.center)
                                if temp_dist < min_dist:
                                    min_dist = temp_dist
                                    best_comb = comb
                            my_comb = self.find_comb(car.position)
                            if best_comb != my_comb:
                                destination = self.find_me_a_destination(best_comb)
                                my_comb.car_sign_out(car)
                                car.relocate(best_comb, self.current_time, destination, init_day_flag, writerIA)
                                #print("Car ", car.vin, " relocating for comb.")
                        else:
                            # There is no comb with insufficient cars - all served
                            results = list()
                            my_comb = self.find_comb(car.position)
                            for comb in self.combs:
                                # check for all ACTIVE combs if minimum number is idle. If not, send car to closest
                                if len(comb.car_list) < self.maximum_cars and comb.active == True:
                                    results.append(comb)
                            time_string = str(self.current_time.hour).zfill(2) + '00'
                            best_value = 0
                            best_comb = None
                            for comb in results:
                                if my_comb.EIT[time_string] is not None and comb.EIT[time_string] is not None:
                                    temp_value = my_comb.EIT[time_string]*60 - comb.EIT[time_string]*60 \
                                                - self.get_distance(car.position, comb.center) #TODO
                                    if temp_value > best_value:
                                        best_value = temp_value
                                        best_comb = comb
                            # This is the threshold - 120 min
                            if best_value > 120*60 and best_comb is not None:
                                destination = self.find_me_a_destination(best_comb)
                                my_comb.car_sign_out(car)
                                car.relocate(best_comb, self.current_time, destination, init_day_flag, writerIA)
                            
        return 0

    def update_module(self, init_day_flag):
        for car in self.cars:
            if car.mode == 'idle':
                if init_day_flag == False:
                    car.count_seconds['idle'] += self.timestep
            elif car.mode == 'active':
                if car.task_list[0]['end time'] < self.current_time:
                    # Yes: Make idle
                    car.task_list.pop(0)
                    car.mode = 'idle'
                    if init_day_flag == False:
                        car.count_seconds['idle'] += self.timestep
                # No: Do nothing
            elif car.mode == 'relocating':
                if car.task_list[0]['end time'] < self.current_time:
                    # Yes: Make idle
                    car.task_list.pop(0)
                    car.mode = 'idle'
                    if init_day_flag == False:
                        car.count_seconds['idle'] += self.timestep
                # No: Do nothing
            elif car.mode == 'charging':
                if car.task_list[0]['end time'] < self.current_time:
                    print("Car ", car.vin, " is done charging. Now it is ", self.current_time, \
                          " and it was done at ", car.task_list[0]['end time'], ". So it leaves ", \
                          car.occupiedCP['UIN'], " which was ", car.occupiedCP['Occupied']
                                                            )
                    # Yes: Make idle
                    car.occupiedCP['Occupied'] = False
                    car.task_list.pop(0)
                    car.mode = 'idle'
                    if init_day_flag == False:
                        car.count_seconds['idle'] += self.timestep
                # No: Do nothing
            elif car.mode == 'locked':
                if car.task_list[0]['end time'] < self.current_time:
                    # Yes: Take next task
                    car.task_list.pop(0)
                    car.mode = car.task_list[0]['mode']
                # No: Do nothing
            elif car.mode == 'ertc':
                if car.task_list[0]['end time'] < self.current_time:
                    # Yes: Take next task
                    car.task_list.pop(0)
                    car.mode = car.task_list[0]['mode']
                # No: Do nothing
            else:
                print("WATCH OUT - THERE HAS BEEN AN ISSUE IN THE UPDATE MODULE IN MODEL.PY ", car.mode, car.vin)
        return 0

    def get_distance(self, start, end):
        #Gives distance in km
        result = haversine.haversine((start['lat'], start['lon']), (end['lat'],end['lon']), miles=False)
        return result

    def create_grid(self):
        # Create the first row of hexagons and measure length
        exit_flag = True
        self.combs.append(comb.comb(self.lat_max, self.lon_max, self.comb_diameter, self.lat_delta, self.lon_delta))
        last_comb = self.combs[-1]
        length_of_first_line = 1.0
        while self.lon_min < last_comb.center_lon:
            self.combs.append(comb.comb(self.lat_max, self.lon_max - 1.5 * length_of_first_line * 4.0 * last_comb.lon_delta, self.comb_diameter, self.lat_delta, self.lon_delta))
            length_of_first_line += 1.0
            last_comb = self.combs[-1]
        while exit_flag:
            # Create the shifted row of hexagons
            this_rows_lat = last_comb.center_lat - last_comb.lat_delta
            this_rows_lon = self.combs[0].center_lon - 0.75 * 4.0 * last_comb.lon_delta
            for i6 in range(int(length_of_first_line)-1):
                self.combs.append(comb.comb(this_rows_lat, this_rows_lon, self.comb_diameter, self.lat_delta, self.lon_delta))
                this_rows_lon -= 1.5 * 4.0 * last_comb.lon_delta
                last_comb = self.combs[-1]
            # Create a concluding full row of hexagons
            this_rows_lat = last_comb.center_lat - last_comb.lat_delta
            this_rows_lon = self.combs[0].center_lon
            for i6 in range(int(length_of_first_line)):
                self.combs.append(comb.comb(this_rows_lat, this_rows_lon, self.comb_diameter, self.lat_delta, self.lon_delta))
                this_rows_lon -= 1.5 * 4.0 * last_comb.lon_delta
                last_comb = self.combs[-1]
            if self.combs[-1].center_lat < self.lat_min:
                exit_flag = False
        return 0

    def deactivate_unused_combs(self):
        for comb in self.combs:
            comb.active = False
        for trip in self.trips:
            temp_comb = self.find_comb(trip.start)
            temp_comb.active = True
            temp_comb = self.find_comb(trip.end)
            temp_comb.active = True
        return 0

    def find_comb(self, point):
        # Returns the comb that a point is in
        for i in self.combs:
            check_inside = self.point_in_comb(i, point)
            if check_inside:
                return i
        print('ERROR! Could not find comb for trip!', point['lat'], ' ', point['lon'])

    def point_in_comb(self, comb, point):
        result = False
        polygon = [[comb.P1['lat'],comb.P1['lon']],[comb.P2['lat'],comb.P2['lon']],\
                   [comb.P3['lat'],comb.P3['lon']],[comb.P4['lat'],comb.P4['lon']],\
                   [comb.P5['lat'],comb.P5['lon']],[comb.P6['lat'],comb.P6['lon']]]
        path = mpltPath.Path(polygon)
        result = path.contains_point([point['lat'],point['lon']])
        return result

    def calculate_EIT_map(self):
        # To estimate idle time for timespan of 4 pm to 5 pm, use all trips that ended between 3:30 pm and 5:30 pm
        for i in range(24): # i between 0 and 23
            # Create a central time based on slot, i.e. 0:30, 1:30 etc
            central_time = datetime.time(hour=i, minute=30, second=0)
            time_string = str(i).zfill(2) + '00'
            for comb in self.combs:
                if comb.active == True:
                    comb.EIT[time_string] = 0.0
                    weight = 0.0
                    for trip in self.EIT_trips:
                        temp_dist = self.get_distance({'lat':comb.center_lat, 'lon':comb.center_lon}, trip.end)
                        if temp_dist <= self.EIT_radius:
                            #This trip is relevant - combwise
                            if i != 0 and i != 23:
                                # All easy times, no date difference
                                if trip.time_end >= datetime.datetime( \
                                        year=trip.time_end.year, month=trip.time_end.month, \
                                        day=trip.time_end.day, hour=central_time.hour, \
                                        minute=central_time.minute, second=central_time.second) \
                                        - self.timewindow_EIT and \
                                   trip.time_end <= datetime.datetime( \
                                        year=trip.time_end.year, month=trip.time_end.month, \
                                        day=trip.time_end.day, hour=central_time.hour, \
                                        minute=central_time.minute, second=central_time.second) \
                                        + self.timewindow_EIT:
                                    #This trip is relevant - timewise
                                    tempweight = self.calcweightEIT(temp_dist)
                                    weight += tempweight
                                    comb.EIT[time_string] += (trip.idle_time.total_seconds() / 60.0) * tempweight
                            else:
                                #Date differences! Watch out
                                if i == 0:
                                    if trip.time_end.hour == 23:
                                        #We have a date gap
                                        temp_date = trip.time_end + datetime.timedelta(days=1)
                                        if trip.time_end >= datetime.datetime( \
                                                year=temp_date.year, month=temp_date.month, \
                                                day=temp_date.day, hour=central_time.hour, \
                                                minute=central_time.minute, second=central_time.second) \
                                                - self.timewindow_EIT and \
                                           trip.time_end <= datetime.datetime( \
                                                year=temp_date.year, month=temp_date.month, \
                                                day=temp_date.day, hour=central_time.hour, \
                                                minute=central_time.minute, second=central_time.second) \
                                                + self.timewindow_EIT:
                                            # This trip is relevant - timewise
                                            tempweight = self.calcweightEIT(temp_dist)
                                            weight += tempweight
                                            comb.EIT[time_string] += (trip.idle_time.total_seconds() / 60.0) * tempweight
                                    else:
                                        # Trip behaves nicely - standard process
                                        if trip.time_end >= datetime.datetime( \
                                                year=trip.time_end.year, month=trip.time_end.month, \
                                                day=trip.time_end.day, hour=central_time.hour, \
                                                minute=central_time.minute, second=central_time.second) \
                                                - self.timewindow_EIT and \
                                           trip.time_end <= datetime.datetime( \
                                                year=trip.time_end.year, month=trip.time_end.month, \
                                                day=trip.time_end.day, hour=central_time.hour, \
                                                minute=central_time.minute, second=central_time.second) \
                                                + self.timewindow_EIT:
                                            # This trip is relevant - timewise
                                            tempweight = self.calcweightEIT(temp_dist)
                                            weight += tempweight
                                            comb.EIT[time_string] += (trip.idle_time.total_seconds() / 60.0) * tempweight
                                else:
                                    if i == 23:
                                        if trip.time_end.hour == 0:
                                            #We have a date gap
                                            temp_date = trip.time_end - datetime.timedelta(days=1)
                                            if trip.time_end >= datetime.datetime( \
                                                    year=temp_date.year, month=temp_date.month, \
                                                    day=temp_date.day, hour=central_time.hour, \
                                                    minute=central_time.minute, second=central_time.second) \
                                                    - self.timewindow_EIT and \
                                                    trip.time_end <= datetime.datetime( \
                                                    year=temp_date.year, month=temp_date.month, \
                                                    day=temp_date.day, hour=central_time.hour, \
                                                    minute=central_time.minute, second=central_time.second) \
                                                    + self.timewindow_EIT:
                                                # This trip is relevant - timewise
                                                tempweight = self.calcweightEIT(temp_dist)
                                                weight += tempweight
                                                comb.EIT[time_string] += (
                                                                         trip.idle_time.total_seconds() / 60.0) * tempweight
                                        else:
                                            # Trip behaves nicely - standard process
                                            if trip.time_end >= datetime.datetime( \
                                                    year=trip.time_end.year, month=trip.time_end.month, \
                                                    day=trip.time_end.day, hour=central_time.hour, \
                                                    minute=central_time.minute, second=central_time.second) \
                                                    - self.timewindow_EIT and \
                                                    trip.time_end <= datetime.datetime( \
                                                    year=trip.time_end.year, month=trip.time_end.month, \
                                                    day=trip.time_end.day, hour=central_time.hour, \
                                                    minute=central_time.minute, second=central_time.second) \
                                                    + self.timewindow_EIT:
                                                # This trip is relevant - timewise
                                                tempweight = self.calcweightEIT(temp_dist)
                                                weight += tempweight
                                                comb.EIT[time_string] += (trip.idle_time.total_seconds() \
                                                                         / 60.0) * tempweight
                    if weight == 0.0:
                        comb.EIT[time_string] = None
                    else:
                        comb.EIT[time_string] = comb.EIT[time_string] / weight
            print('Hour ', i, ' has been calculated.')
        return 0

    def calcweightEIT(self, distance):
        result = 1.0 - distance /self.EIT_radius
        if result < 0.0:
            result = 0.0
        return result

    def write_EIT_map(self, path):
        wr1file = open(path, 'w')
        writer1 = csv.writer(wr1file, delimiter=";", lineterminator='\n')
        header1 = ('Center-lat', 'Center-lon', 'Active', \
                   '0000', '0100', '0200', '0300', \
                   '0400', '0500', '0600', '0700', \
                   '0800', '0900', '1000', '1100', \
                   '1200', '1300', '1400', '1500', \
                   '1600', '1700', '1800', '2200', \
                   '2000', '2100', '2200', '2300')
        writer1.writerow(header1)
        for comb in self.combs:
            header1 = (comb.center_lat, comb.center_lon, comb.active, \
                       comb.EIT['0000'], comb.EIT['0100'], comb.EIT['0200'], comb.EIT['0300'], \
                       comb.EIT['0400'], comb.EIT['0500'], comb.EIT['0600'], comb.EIT['0700'], \
                       comb.EIT['0800'], comb.EIT['0900'], comb.EIT['1000'], comb.EIT['1100'], \
                       comb.EIT['1200'], comb.EIT['1300'], comb.EIT['1400'], comb.EIT['1500'], \
                       comb.EIT['1600'], comb.EIT['1700'], comb.EIT['1800'], comb.EIT['1900'], \
                       comb.EIT['2000'], comb.EIT['2100'], comb.EIT['2200'], comb.EIT['2300'])
            writer1.writerow(header1)
            wr1file.flush()
        wr1file.close()
        return 0

    def calculate_lon_lat_delta(self):
        # latitude
        lat_dist_temp = haversine.haversine((self.trips[0].start['lat'], self.trips[0].start['lon']), \
                                            (self.trips[0].start['lat'] + 0.1, self.trips[0].start['lon']), miles=False)
        self.lat_delta = (self.comb_diameter * (math.sqrt(3.0) / 4.0) * 0.1) / lat_dist_temp
        # longitude
        lon_dist_temp = haversine.haversine((self.trips[0].start['lat'], self.trips[0].start['lon']), \
                                            (self.trips[0].start['lat'], self.trips[0].start['lon'] + 0.1), miles=False)
        self.lon_delta = (self.comb_diameter * 0.25 * 0.1) / lon_dist_temp
        return 0

    def save_results(self):
        wrVSfile = open(r'./_results/Vehicle_stats.csv', 'w')
        writer1 = csv.writer(wrVSfile, delimiter=";", lineterminator='\n')
        header1 = ('VIN', 'Requests', 'Relocations', 'Chargings', 'Minutes Idle', \
                   'Minutes Active', 'Minutes Locked', 'Minutes Relocating', \
                   'Minutes Charging', 'Minutes ERTC', 'KM Active', 'KM Locked', \
                   'KM Relocating', 'KM ERTC')
        writer1.writerow(header1)
        for car in self.cars:
            header1 = (car.vin, car.count_requests_accepted, car.count_times['relocating'], \
                       car.count_times['charging'], car.count_seconds['idle']/60.0, \
                       car.count_seconds['active']/60.0, car.count_seconds['locked']/60.0, \
                       car.count_seconds['relocating']/60.0, car.count_seconds['charging']/60.0,\
                       car.count_seconds['ertc']/60.0, car.count_km['active'], car.count_km['locked'], \
                       car.count_km['relocating'], car.count_km['ertc'])
            writer1.writerow(header1)
            wrVSfile.flush()
        wrVSfile.close()
        return 0

    def write_missed_request(self, init_day_flag, writerIA, current_requests):
        for request in current_requests:
            lineforwriter = ('---', \
                             'MISSED REQUEST', \
                             request.time_start, \
                             request.time_end, \
                             request.start['lat'], \
                             request.start['lon'], \
                             request.end['lat'], \
                             request.end['lon'], \
                             '---', \
                             init_day_flag)
            writerIA.writerow(lineforwriter)
        return 0

    def CP_module(self):
        i_CP = 0
        i_popped = 0
        print("We have ", len(self.CPs), " Charging Points. Cleaning...")
        for CP in self.CPs:
            hit = False
            for comb in self.combs:
                if comb.active:
                    if self.point_in_comb(comb, {'lat':CP['lat'], 'lon':CP['lon']}):
                        hit = True
            if hit == False:
                self.CPs[i_CP]['UIN'] = None
                i_popped += 1
            i_CP += 1
        print("Now we have ", len(self.CPs)-i_popped, " Charging Points. Shuffling and saving...")
        shuffle(self.CPs)
        wrCPfile = open(r'./_init/Charge_Points.csv', 'w')
        writer1 = csv.writer(wrCPfile, delimiter=";", lineterminator='\n')
        header1 = ('UIN', 'Latitude', 'Longitude', 'Power')
        writer1.writerow(header1)
        for CP in self.CPs:
            if CP['UIN'] is not None:
                header1 = (CP['UIN'], CP['lat'], CP['lon'], CP['Power'])
                writer1.writerow(header1)
                wrCPfile.flush()
        wrCPfile.close()
        print("Charging Points saved.")
        return 0

    def load_CPs_csv(self, number_of_CPs):
        self.CPs = list()
        readCPfile = open(r'./_init/Charge_Points.csv', 'r')
        reader1 = csv.reader(readCPfile, delimiter=";", lineterminator='\n')
        for row in reader1:
            if row[0] != 'UIN':
                self.CPs.append({'UIN':int(row[0]), 'lat':float(row[1]), 'lon':float(row[2]), 'Occupied':False, 'Power':float(row[3])})
                if len(self.CPs) >= number_of_CPs:
                    break
        print(len(self.CPs), " Charging Points loaded.")
        return 0