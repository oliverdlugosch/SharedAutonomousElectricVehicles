import datetime

class trip(object):
    def __init__(self, start, end, time_start, time_end, idle_time, vin):
        self.start = start
        self.end = end
        self.time_start = datetime.datetime.strptime(time_start, "%Y-%m-%d %H:%M:%S.%f")
        self.time_end = datetime.datetime.strptime(time_end, "%Y-%m-%d %H:%M:%S.%f")
        self.idle_time = idle_time
        self.vin = vin
        self.rental_time = self.time_end - self.time_start
        self.firstofday = False     #True if the trip is the first trip of the day
        self.tripsthisday = None    #Number of trips on this day
        self.UIN = None             #Unique identification number for each trip
        self.duration = self.time_end - self.time_start
