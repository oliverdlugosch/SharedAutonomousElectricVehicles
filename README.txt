Dear user,

We have set up a test data set for you to see if the code works properly. To check this, please follow these steps:
1) Keep "config.ini" structured as it is and place it in a folder called "_init" which should be located in the same directory that these python files are in.
2) Create a folder called "_results" which should be located in the same directory that these python files are in.
3) Charge_Points.csv contains a charge point list that can be filled to set charge point location and charging power in kW. Place in _init to use it.
4) berlin.json contains a list of charge points that is used to select the determined number of charge points randomly. Place in _init to use it. Creates "Charge_Points.csv" when used to shuffle charge points for future reproducibility. Further details in model.py.
5) Within _init, please place the trip data as a file in <location name>.db format. We have placed a sample data set for Berlin.
6) Set up a routing server based on https://github.com/Project-OSRM/osrm-backend and copy the respective IP of the routing server into the according position within "_init/config.ini"
7) To start the simulation, run _main.py.
