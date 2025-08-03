#無正式環境API
sim_api_key= "Dr9os79UkacqMRzDPbenbp1Au6AVLHfwgzxhvesxfpkk"     
sim_secret_key= "DvuFwczTroTYtH1JYHeZ5sNwFQ9b3mXbHvqK5PMEtFWs" 

sim_api_key= "72mawBKMAvP3Y3A6xKwTwytbjsPRjTQYx8SqrYF5kX5P"     
sim_secret_key= "57k5Y9SsPTWUasDJfDEw1MqLsJWE2zS1ykUcoWEG4t8d" 


#正式環境API
real_api_key = ""     #自行填入 #
real_secret_key = ""     #自行填入 


def get_Key(Sim):
    if Sim == True:
        return sim_api_key
    elif Sim == False:
        return real_api_key
    else:
        print("The input of Sim should be True or False.")
        return None
    
def get_Secret(Sim):
    if Sim == True:
        return sim_secret_key
    elif Sim == False:
        return real_secret_key
    else:
        print("The input of Sim should be True or False.")
        return None
    
