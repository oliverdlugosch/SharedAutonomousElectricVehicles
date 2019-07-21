import haversine, math, car

class comb(object):
    def __init__(self, center_lat = None, center_lon = None, radius = None, lat_delta = None, lon_delta = None, active = True):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.center = {'lat': center_lat, 'lon': center_lon}
        self.active = active
        self.radius = radius
        self.lat_delta = lat_delta
        self.lon_delta = lon_delta
        self.car_list = list()
        self.P1 = dict()
        self.P2 = dict()
        self.P3 = dict()
        self.P4 = dict()
        self.P5 = dict()
        self.P6 = dict()
        self.create_polygon(center_lat, center_lon, self.lat_delta, self.lon_delta)
        self.EIT = {'0000': 0.0, '0100': 0.0, '0200': 0.0, '0300': 0.0, \
                    '0400': 0.0, '0500': 0.0, '0600': 0.0, '0700': 0.0, \
                    '0800': 0.0, '0900': 0.0, '1000': 0.0, '1100': 0.0, \
                    '1200': 0.0, '1300': 0.0, '1400': 0.0, '1500': 0.0, \
                    '1600': 0.0, '1700': 0.0, '1800': 0.0, '1900': 0.0, \
                    '2000': 0.0, '2100': 0.0, '2200': 0.0, '2300': 0.0}

    def create_polygon(self, center_lat, center_lon, lat_delta, lon_delta):
        self.P1['lat'] = center_lat
        self.P1['lon'] = center_lon + 2.0 * lon_delta
        self.P2['lat'] = center_lat + lat_delta
        self.P2['lon'] = center_lon + 1.0 * lon_delta
        self.P3['lat'] = center_lat + lat_delta
        self.P3['lon'] = center_lon - 1.0 * lon_delta
        self.P4['lat'] = center_lat
        self.P4['lon'] = center_lon - 2.0 * lon_delta
        self.P5['lat'] = center_lat - lat_delta
        self.P5['lon'] = center_lon - 1.0 * lon_delta
        self.P6['lat'] = center_lat - lat_delta
        self.P6['lon'] = center_lon + 1.0 * lon_delta
        return 0

    def car_sign_in(self, car):
		# car joings the comb
        self.car_list.append(car)
        return 0

    def car_sign_out(self, car_to_pop):
		# car leaves the comb
        i_temp = 0
        target_i = 0
        for car in self.car_list:
            if car.vin == car_to_pop.vin:
                target_i = i_temp
            i_temp += 1
        if len(self.car_list) != 0:
            self.car_list.pop(target_i)
        return 0



