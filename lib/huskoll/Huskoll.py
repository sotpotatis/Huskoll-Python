"""Huskoll.py
The code for this very simple library.
The library contains one main class, which is Device,
and then the subclass Status representing the device status.
The Device represents a physical Huskoll device.
"""
import requests, dateutil.parser, warnings #Import required libaries
from .Exceptions import * #Import all exceptions for the library.

#URLs for interacting with the API
SET_PARAMETERS_URL = "https://huskoll.se/API/openAPI.php/huskoll/set/"
GET_PARAMETERS_URL = "https://huskoll.se/API/openAPI.php/huskoll/get/"

class Device(object):

    """The main class. Represents a Huskoll Device"""

    #Some helpful variables:
    #Fan modes:
    FAN_AUTO = "auto"
    FAN_LOW = "low"
    FAN_MEDIUM = "medium"
    FAN_HIGH = "high"

    #Heating modes
    COOL = "cool"
    HEAT = "heat"

    #Power modes
    POWER_OFF = "off"
    POWER_ON = "on"

    def __init__(self, hardware_id, token):
        """Initializing function.
        Hardware_ID is the Hardware ID of the actual Huskoll Device
        The token can, according to the official docs, be requested from the Huskoll support."""
        self.hardware_id = hardware_id
        self.token = token
        self.status = None #The device status.
        self.status_json = None #The device status as returned raw by the server
        self.hardware_generation = None #The device hardware generation
        #TODO: Add values for the last device status update

    def generate_request_auth(self):
        """Function for generating the auth parameters data that should be supplied by every request."""
        return {"token": self.token, "hwid": self.hardware_id} #Return the data

    def get_status(self):
        """Function for getting the status of the device."""
        r = requests.post(GET_PARAMETERS_URL, data=self.generate_request_auth()) #Send a request to the server
        try: #Attempt to convert the response to JSON.
            resp_json = r.json()
        except Exception as e: #In case of an error
            warnings.warn(f"Failed to decode response text {r.text} to JSON. Make sure the supplied token and hardware ID is correct.")
            raise e #Raise the original exception
        #Check if an error was returned:
        if "error" in resp_json.keys(): #If the error key exists in the response
            error_message = resp_json["error"] #Get the error message
            return ResponseError(f"Huskoll server returned the following error: {error_message}") #Raise an exception with the error returned by the server

        #Create a Status object with the provided information:
        self.hardware_generation = resp_json["hw_generation"] #Get the hardware version and set it for the Device object.
        self.status = Status(
            status=resp_json["status"], #The device status
            power=resp_json["power"], #The pump power status
            mode=resp_json["mode"], #The pump mode
            current_set_point=float(resp_json["setpoint"]), #The pump sent temperature
            fan_speed=resp_json["fan"], #The pump set fan speed
            current_env_temperature=float(resp_json["temperature"]), #The current room temperature (I assume?)
            last_alarm=dateutil.parser.parse(resp_json["alarm"].split("UTC")[0]), #When an alarm was last triggered (I assume?)
            #Note: Huskoll's API returns something weird after the time definition for the last alarm - it looks like "UTC T<10".
            #This string is not part of any standard, so this library simply leaves it out.
            hardware_generation=self.hardware_generation #The hardware generation of the device
        )
        return self.status #Return the device status

    def update_status(self, new_power_status=None, new_mode=None, new_fan_speed=None, new_temperature=None):
        """Function for updating the status of a device.
        All parameters should be sent in one request according to the docs,
        so if all parameters are not specified, the device status is first retrieved,
        and the blank parameters are set to its current value, assuming they should not be changed."""
        if None in [new_power_status, new_mode, new_fan_speed, new_temperature]: #If any of the passed kwargs are None
            device_status = self.get_status() #Get the device status
            #Make sure all variables are specified using the newly retrieved variables from the device status
            if new_power_status == None: new_power_status = device_status.power
            if new_mode == None: new_mode = device_status.mode
            if new_fan_speed == None: new_fan_speed = device_status.fan_speed
            if new_temperature == None: new_temperature = device_status.current_set_point
         #The data to supply with the request. Start with the required authentication parameters
        #Make sure the data object is complete
        data = {**self.generate_request_auth()} #Generate the data to send with the request. Include the authentication as a start.
        #and... update the data to send and the device's local status with the set parameters:
        self.status.power = data["power"] = new_power_status
        self.status.mode = data["mode"] = new_mode
        self.status.fan_speed = data["fan"] = new_fan_speed
        self.status.current_set_point = data["setpoint"] = str(new_temperature)
        #Send the device update request
        r = requests.post(SET_PARAMETERS_URL, data=data) #Send a request to the server
        try: #Attempt to convert the response to JSON.
            resp_json = r.json()
        except Exception as e: #In case of an error
            warnings.warn(f"Failed to decode response text {r.text} to JSON. Make sure the supplied token and hardware ID is correct.")
            raise e #Raise the original exception
        #The response should according to the API docs be "status": "ack".
        if "status" in resp_json.keys(): #If the status key is present in the body
            status = resp_json["status"].lower() #Get the status and convert it to lowercase.
            #Parse the status as returned by the Huskoll API.
            if status == "nak": #Most likely means not acknowledged, this is not stated in their API docs.
                raise ResponseError("Server responded with nak (set data not acknowledged).")
            elif status != "ack": #If the status is not "ack", which is what we should be getting
                raise ResponseError(f"Server responded with an unknown response: {status}.")
            #(if the status is ack, this function will just continue)
        else:
            raise ResponseError(f"\"status\" key not present in body! (body: {resp_json})")

    #Shortcut functions for interacting with the device.
    def power_off(self):
        """Function for powering off the device.
        Updates the power status parameter."""
        self.update_status(new_power_status=self.POWER_OFF)

    def power_on(self):
        """Function for powering on the device.
        Updates the power status parameter."""
        self.update_status(new_power_status=self.POWER_ON)

    def set_cooling(self):
        """Function for setting the device heat mode to cooling.
        Updates the mode parameter."""
        self.update_status(new_mode=self.COOL)

    def set_heating(self):
        """Function for setting the device heat mode to heating.
        Updates the mode parameter."""
        self.update_status(new_mode=self.HEAT)

    def fan_speed_auto(self):
        """Function for setting the device fan speed to auto.
        Updates the fan speed parameter."""
        self.update_status(new_fan_speed=self.FAN_AUTO)

    def fan_speed_low(self):
        """Function for setting the device fan speed to low.
        Updates the fan speed parameter."""
        self.update_status(new_fan_speed=self.FAN_LOW)

    def fan_speed_medium(self):
        """Function for setting the device fan speed to medium.
        Updates the fan speed parameter."""
        self.update_status(new_fan_speed=self.FAN_MEDIUM)

    def fan_speed_high(self):
        """Function for setting the device fan speed to high.
        Updates the fan speed parameter."""
        self.update_status(new_fan_speed=self.FAN_HIGH)

    def set_temp(self, new_temp, suppress_warning=False):
        """Function for setting the device to a new temperature"""
        """According to the Huskoll API docs, the point can be set 
        between 8-32. So, let's warn if that is not the case."""
        if new_temp < 8 or new_temp > 32 and not suppress_warning: #If the set point might not be supported by Huskoll
            warnings.warn("""The set temperature might be out of range of what Huskoll supports.
            Refer to their API documentation. Set suppress_warning to True in the function call to get
            rid of this value.""")
        self.update_status(new_temperature=new_temp)

    def change_temperature(self, by=1, force_status_update=False):
        """Function for changing the set temperature goal
        (set point) of the device by a certain steps.
        Takes two optional keywords:
        by - what to change the temperature with
        force_status_update - if not True, the device will use its stored status data
        if it has read the status"""
        if self.status == None or force_status_update: #If we need to re-get the current device status
            self.get_status() #Get the current device status
        current_set_point = self.status.current_set_point #Get the current set point
        current_set_point += by #Increase the current set point to create a goal point
        self.update_status(new_temperature=current_set_point) #Update the device set temperature goal

    def decrease_temperature(self, by=1, force_status_update=False):
        """Function for increasing the set temperature goal
        (set point) of the device by a certain steps.
        Simply calls change_temperature above - see that one for a definition of kwargs."""
        by = abs(by) #Make the by variable negative so that it calls the change_temperature function correctly
        self.change_temperature(by=by, force_status_update=force_status_update) #Call the parent function

    def increase_temperature(self, by=1, force_status_update=False):
        """Function for decreasing the set temperature goal
        (set point) of the device by a certain steps.
        Simply calls change_temperature above - see that one for a definition of kwargs."""
        self.change_temperature(by=by, force_status_update=force_status_update) #Call the parent function

class Status(object):
    """The status class represents the device status. The current
    status can be retrieved from the status variable of a Device object."""
    def __init__(self, status, power, mode, current_set_point, fan_speed, current_env_temperature, last_alarm, hardware_generation):
        """Initialization function. All of these values are initiated by the get_status()
        function of Device."""
        self.status = status
        self.power = power
        self.mode = mode
        self.current_set_point = float(current_set_point)
        self.fan_speed = fan_speed
        self.current_env_temperature = float(current_env_temperature)
        self.last_alarm = last_alarm
        self.hardware_generation = hardware_generation
