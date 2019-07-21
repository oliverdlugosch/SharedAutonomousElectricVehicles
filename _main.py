import model, readin

# Reading config file
path = r'./_init/config.ini'
input_config = readin.readin(path)

# Create model
thismodel = model.model(input_config['location'], input_config['number_of_cars'], \
                        input_config['number_of_CPs'], input_config['firstday'], \
                        input_config['lastday'], input_config['trainingpercentage'], \
                        input_config['timestep'], input_config['EIT_radius'], \
                        input_config['Comb_diameter'], input_config['ip_address'], \
                        input_config['minimum cars'], input_config['maximum cars'])

# Run simulations
thismodel.run()

# Save results
thismodel.save_results()


